#!/bin/sh
cd ./pdbs/
for r in ./*.pdb; do
	
        name=${r%".pdb"}
	echo "in $name"
	stride $r -rA -f../files_native/"${name}A"
done
