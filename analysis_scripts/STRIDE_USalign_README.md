# Analysis of local and global structural similarity of predicted protein structures:

STRIDE (STRuctural IDEntification) and US-align batch data extraction

## Requirements

* Python 3.9
* Pandas
* Numpy
* Bash (optional)

## Usage


### Extract and calculate secondary structure conservation in proportion to position identified by STRIDE using `stride_extract.py`

1. Generate reports using command-line or web-server versions of STRIDE (available: http://webclu.bio.wzw.tum.de/stride/) for native and predicted structures with the default output format. Place native and predicted results in separate directories.
   - bash automation scripts stride_script_n.sh (native) and stride_script.sh (predicted) can be used - input PDB files factored pdbs/pdb1xyz.pdb and AlphaFold/1XYZA/1XYZA*.pdb, respectively
   - note that the chain should be specified if bash scripts are used
2. Run stride_extract.py specifying directories and chain accession code in the format 1XYZA for chain A of protein 1XYZ.

        stride_extract.py native_directory predicted_directory 1XYZA
   
    - files_native and files directories contain examples of result files
    - predicted result files should be named leading with the chain code in the format described

### Generate, extract and summarise RMSD and TM-score values with US-align as measure of global similarity using `us_extract.py`:

1. Generate reports using command-line or web-server versions of US-align (available: https://zhanggroup.org/US-align/) for each predicted structure.
   - a bash automation script can be used - input PDB files factored pdbs/pdb1xyz.pdb and AlphaFold/1XYZA/1XYZA*.pdb, respectively
   - note that the scripts should be edited to be chain-specific 
2. Run us_extract.py specifying the raw data directory with chains separated in subdirectories, optionally selecting a single chain. 
   us_extract.py directory

        us_extract.py report_directory -c 1XYZA

   - chain (-c) specifies a chain. If omitted, all chain are processed. 
   - raw_data directory contains examples of reports 