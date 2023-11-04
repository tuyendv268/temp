import re
import os
from glob import glob
from tqdm import tqdm

def postprocess(textgrid):
    paragraphs = textgrid.split("item")

    pattern = "intervals\s\[[0-9]+\]:\n\s*xmin\s=\s([0-9\.]+)\s*\n\s+xmax\s=\s([0-9\.]+)\s*\n\s*text\s=\s\"\""
    temp = paragraphs[-1]
    new_text_grid = []
    while re.search(pattern=pattern, string=temp) is not None:
        matched = re.search(pattern, temp)
        
        start = float(re.findall(pattern, temp)[0][0])
        end = float(re.findall(pattern, temp)[0][1])
        
        # if 0.1<=(end-start) and (end-start)<0.2:
        #     _temp = matched.group().replace('text = ""', 'text = "sil" ')
        if 0.2<=(end-start) and (end-start)<0.5:
            _temp = matched.group().replace('text = ""', 'text = "sp" ')
        elif (end-start)>=0.5:
            _temp = matched.group().replace('text = ""', 'text = "dot" ')
        else:
            _temp = matched.group()
        
        new_text_grid.append([matched.group(), _temp])
        temp = temp[matched.span()[1]:]
        
    text_grid = paragraphs[-1]
    for sample in new_text_grid[1:-1]:
        text_grid = text_grid.replace(sample[0], sample[1])
    paragraphs[-1] = text_grid
    
    text_grid = "item".join(paragraphs)
    
    return text_grid

def do_postprocess(in_dir, out_dir):
    for _file in tqdm(glob(f'{in_dir}/*.TextGrid')):
        with open(_file, "r", encoding="utf-8") as f:
            textgrid = f.read()
        
        textgrid = postprocess(textgrid)
        
        out_path = f'{out_dir}/{os.path.basename(_file)}'
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(textgrid)
            
if __name__ == "__main__":
    in_dir = "/data/codes/speech-to-text/stt/data/corpus/origin-textgrid"
    out_dir = "/data/codes/speech-to-text/stt/data/corpus/textgrid"
    
    do_postprocess(
        in_dir=in_dir,
        out_dir=out_dir
    )