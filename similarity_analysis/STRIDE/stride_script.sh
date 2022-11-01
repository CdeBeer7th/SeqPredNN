#!/bin/sh
for d in ./AlphaFold/*/ ; do
	
	cd $d
	
	for f in ./*/; do
		cd $f
		for r in ./*rank_1*.pdb; do
			
			name=${f#"./"}
			name=${name%"/"}
			echo "in $r, out $name"
			stride $r -f../../../files/"$name"
		done
		cd ..
	done
	cd ../..
done

