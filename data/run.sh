# write a bash script that change all directory name in ./myc/* to opencv_calib3d__<bug_num>__<originalname>
# where bug_num increments from 1 to the number of directories in ./myc/

#!/bin/bash
bug_num=1
for dir in ./myc/*/; do
    originalname=$(basename "$dir")
    newname="opencv_calib3d__${bug_num}__${originalname}"
    mv "$dir" "./myc/${newname}"
    ((bug_num++))
done