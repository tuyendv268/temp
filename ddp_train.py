import argparse
import os

import torch
import yaml
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.utils.tensorboard import SummaryWriter
from torch.utils.data.distributed import DistributedSampler
from tqdm.auto import tqdm

from utils.model import get_model, get_vocoder, get_param_num
from utils.tools import to_cuda, log, synth_one_sample
from model import FastSpeech2Loss
from dataset import Dataset
import numpy as np
import torch.distributed as dist
from evaluate import evaluate

def is_dist_avail_and_initialized():
    if not dist.is_available():
        return False

    if not dist.is_initialized():
        return False

    return True

def save_on_master(*args, **kwargs):
    if is_main_process():
        torch.save(*args, **kwargs)

def get_rank():
    if not is_dist_avail_and_initialized():
        return 0

    return dist.get_rank()

def is_main_process():
    return get_rank() == 0

def setup_for_distributed(is_master):
    """
    This function disables printing when not in master process
    """
    import builtins as __builtin__
    builtin_print = __builtin__.print

    def print(*args, **kwargs):
        force = kwargs.pop('force', False)
        if is_master or force:
            builtin_print(*args, **kwargs)

    __builtin__.print = print


def init_distributed():
    dist_url = "env://"
    
    rank = int(os.environ["RANK"])
    world_size = int(os.environ['WORLD_SIZE'])
    local_rank = int(os.environ['LOCAL_RANK'])

    dist.init_process_group(
            backend="nccl",
            init_method=dist_url,
            world_size=world_size,
            rank=rank)

    torch.cuda.set_device(local_rank)
    # synchronizes all the threads to reach this point before moving on
    dist.barrier()
    setup_for_distributed(rank == 0)


def main(args, configs):    
    init_distributed()
    
    preprocess_config, model_config, train_config = configs
    dataset = Dataset(
        "train.txt", preprocess_config, train_config, sort=True, drop_last=True
    )
    print(len(dataset))
    sampler = DistributedSampler(dataset=dataset, shuffle=True)
    batch_size = train_config["optimizer"]["batch_size"]
    group_size = 4

    device = "cuda"
    local_rank = int(os.environ['LOCAL_RANK'])
    model, optimizer = get_model(args, configs, device, train=True)
    model = model.cuda()
    model = nn.parallel.DistributedDataParallel(model, device_ids=[local_rank])

    loader = DataLoader(
        dataset,
        batch_size=batch_size * group_size,
        shuffle=False,
        sampler=sampler,
        num_workers=1,
        collate_fn=dataset.collate_fn
        )
    num_param = get_param_num(model)

    Loss = FastSpeech2Loss(preprocess_config, model_config).cuda()
    print("Number of FastSpeech2 Parameters:", num_param)
    vocoder = get_vocoder(model_config, device)
    vocoder = vocoder.cuda()
    
    if is_main_process():
        for p in train_config["path"].values():
            os.makedirs(p, exist_ok=True)
        train_log_path = os.path.join(train_config["path"]["log_path"], "train")
        val_log_path = os.path.join(train_config["path"]["log_path"], "val")
        os.makedirs(train_log_path, exist_ok=True)
        os.makedirs(val_log_path, exist_ok=True)
        train_logger = SummaryWriter(train_log_path)
        val_logger = SummaryWriter(val_log_path)

    # Training
    step = args.restore_step + 1
    epoch = 1
    grad_acc_step = train_config["optimizer"]["grad_acc_step"]
    grad_clip_thresh = train_config["optimizer"]["grad_clip_thresh"]
    total_step = train_config["step"]["total_step"]
    log_step = train_config["step"]["log_step"]
    save_step = train_config["step"]["save_step"]
    synth_step = train_config["step"]["synth_step"]
    val_step = train_config["step"]["val_step"]
    
    print("Start Training: ")
    scaler = torch.cuda.amp.GradScaler(enabled=True)
    
    while True:
        # _bar = tqdm(loader, total=len(loader), desc=f"Training: gid={get_rank()}", position=1)
        current_losses = []
        loader.sampler.set_epoch(epoch)
        for batchs in loader:
            for batch in batchs:
                batch = to_cuda(batch)

                with torch.cuda.amp.autocast(dtype=torch.float16):
                    output = model(*(batch[2:]))

                    losses = Loss(batch, output)
                    total_loss = losses[0]

                    total_loss = total_loss / grad_acc_step
                    
                scaler.scale(total_loss).backward()

                if step % grad_acc_step == 0:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip_thresh)
                    # Update weights
                    optimizer._update_learning_rate()
                    scaler.step(optimizer._optimizer)
                    optimizer.zero_grad()
                    scaler.update()

                if is_main_process():
                    losses = [l.item() for l in losses]
                    current_losses.append(losses)
                    if step % log_step == 0:
                        message1 = "### Training log at step {}/{}: \n".format(step, total_step)
                        message2 = "Total Loss: {:.4f}:\n Mel Loss: {:.4f}, Mel PostNet Loss: {:.4f}, Pitch Loss: {:.4f}, Energy Loss: {:.4f}, Duration Loss: {:.4f}\n".format(
                            *losses)

                        with open(os.path.join(train_log_path, "log.txt"), "a") as f:
                            f.write(message1 + message2 + "\n")

                        print(message1 + message2)

                    if step % synth_step == 0:
                        with torch.cuda.amp.autocast(dtype=torch.float16):
                            fig, wav_reconstruction, wav_prediction, tag = synth_one_sample(
                                batch,
                                output,
                                vocoder,
                                model_config,
                                preprocess_config,)
                        # log(
                        #     train_logger,
                        #     fig=fig,
                        #     tag="Training/step_{}_{}".format(step, tag),)
                        sampling_rate = preprocess_config["preprocessing"]["audio"]["sampling_rate"]
                        log(
                            train_logger,
                            audio=wav_reconstruction,
                            sampling_rate=sampling_rate,
                            tag="Training/step_{}_{}_reconstructed".format(step, tag))
                        log(
                            train_logger,
                            audio=wav_prediction,
                            sampling_rate=sampling_rate,
                            tag="Training/step_{}_{}_synthesized".format(step, tag))

                    if step % val_step == 0:
                        model.eval()
                        with torch.cuda.amp.autocast(dtype=torch.float16):
                            message = evaluate(model, step, configs, device, val_logger, vocoder)
                        with open(os.path.join(val_log_path, "log.txt"), "a") as f:
                            f.write(message + "\n")
                        print(message)

                        model.train()

                    if step % save_step == 0:
                        torch.save(
                            {
                                "model": model.module.state_dict(),
                                "optimizer": optimizer._optimizer.state_dict(),
                            },
                            os.path.join(
                                train_config["path"]["ckpt_path"],
                                "{}.pth.tar".format(step),),
                        )

                if step == total_step:
                    quit()
                step += 1
                # _bar.set_postfix(
                #     {
                #         "step": str(step),
                #         "epoch": epoch,
                #         "rank": get_rank()
                #         }
                #     )
                # _bar.update()
        epoch += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore_step", type=int, default=0)
    parser.add_argument("-p", "--preprocess_config", type=str, required=True, help="path to preprocess.yaml")
    parser.add_argument("-m", "--model_config", type=str, required=True, help="path to model.yaml")
    parser.add_argument("-t", "--train_config", type=str, required=True, help="path to train.yaml")
    
    args = parser.parse_args()
    
    preprocess_config = yaml.load(open(args.preprocess_config, "r"), Loader=yaml.FullLoader)
    model_config = yaml.load(open(args.model_config, "r"), Loader=yaml.FullLoader)
    train_config = yaml.load(open(args.train_config, "r"), Loader=yaml.FullLoader)
    
    configs = (preprocess_config, model_config, train_config)
    
    main(args, configs)