export OMP_NUM_THREADS=1
torchrun --nnodes=1 \
        --nproc_per_node=2 \
        ddp_train.py \
            --preprocess_config configs/preprocess.yaml \
            --model_config configs/model.yaml \
            --train_config configs/train.yaml \
            --restore_step 100000