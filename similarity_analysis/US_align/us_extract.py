import pandas as pd
import pathlib
import os
import argparse

def get_args():
    arg_parser = argparse.ArgumentParser(description="Extract RMSD and TM-scores calculated with US-align.")
    arg_parser.add_argument('directory', type=str, help="US-align reports. Chains separated by"
                                                        " independent subdirectories named according"
                                                        " to chain code in format 1XYZA.")

    arg_parser.add_argument('-c', '--chain', type=str, default='*', help="Chain code in the format 1XYZA. "
                                                                          "If omitted, all chains are extracted.")
    args = arg_parser.parse_args()
    return args.directory, args.chain

def main():
    directory, selected_chain = get_args()

    m_path = pathlib.Path(directory).glob(f'{selected_chain}')
    if not pathlib.Path('results').exists():
        os.mkdir('results')
    for path in m_path:
        files = pathlib.Path(path).glob('*')
        chain = (str(path).split('\\')[-1])
        tm = []
        rmsd = []
        seq = []
        for file in files:
            pan = pd.read_table(file)
        raw_df = pd.DataFrame(pan)
        raw_df = raw_df.rename(columns={f"{str(raw_df.columns[0])}": "value"})
        raw_df = raw_df[raw_df.value.str.contains("TM-score|Aligned length")]
        raw_df = raw_df.value.str.split(expand=True)
        df = raw_df[[1, 4]]
        tm.append(df[1].apply(pd.Series).stack().tolist()[1])
        rmsd.append(df[4].apply(pd.Series).stack().tolist()[0][0:-1])
        seq.append(str(file).split('\\')[-1].replace('.txt', ''))
        df = pd.DataFrame({'Sequence': seq, 'TM-Score': tm, 'RMSD': rmsd})
        df.to_csv(pathlib.Path(f'results/{chain}.csv'))

main()