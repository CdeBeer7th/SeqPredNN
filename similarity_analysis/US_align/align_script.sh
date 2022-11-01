#!/bin/sh

for f in ./AlphaFold/1SHRB/*/ ; do
	for r in $f*rank_1*.pdb; do
		name=${f#"./AlphaFold/"}
		name=${name%"/"}
		echo "$r $name"
		mkdir ../us_out/1SHRB
		./USalign $r ./pdbs/pdb1shr.pdb -ter 0 > ../us_out/"$name".txt
	done

done

