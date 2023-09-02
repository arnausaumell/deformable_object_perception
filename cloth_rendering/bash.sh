#!/bin/bash
scene_name=$1
echo "Processing dataset: $scene_name\n"

python3 masking.py -s $scene_name
python3 correct_annotations.py -s $scene_name
cd pdc/logs_proto
zip -r $scene_name.zip $scene_name
scp -r $scene_name.zip aportillo@txe1-login.mit.edu:pytorch-dense-correspondence/pdc/logs_proto

# ssh aportillo@txe1-login.mit.edu
# cd pytorch-dense-correspondence/pdc/logs_proto
# unzip $scene_name.zip
# rm -rf $scene_name.zip