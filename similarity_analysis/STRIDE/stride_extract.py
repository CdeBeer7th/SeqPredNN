import pandas as pd
import numpy as np
import pathlib
import os
import argparse

def get_args():
    arg_parser = argparse.ArgumentParser(description="Extract and calculate percentage of secondary structure "
                                                     "conservation determined by STRIDE for large batches of reports")
    arg_parser.add_argument('native_directory', type=str, help="directory of native chain reports in format 1XYZA")
    arg_parser.add_argument('predicted_directory', type=str, help="Parent directory of predicted chain results."
                                                                  "File names in any format - same convention will be"
                                                                  " used for results.")
    arg_parser.add_argument('chain', type=str, help="chain code in the format 1XYZA")
    args = arg_parser.parse_args()
    return args.native_directory, args.predicted_directory, args.chain

def main():
    native_directory, predicted_directory, chain = get_args()
    print(get_args())
    path = pathlib.Path(predicted_directory).glob('*')
    n_chain = f'{chain}'
    n_file = f"./{native_directory}/{n_chain}"
    path_native = pathlib.Path(n_file)
    pan = pd.read_table(path_native)
    df = pd.DataFrame(pan)
    df = df.rename(columns={f"{str(df.columns[0])}" : "value"})
    df = df.value.str.split(expand=True)
    df = df[df[0].str.contains("ASG")]
    df = df.rename(columns={6 : "NativeSecondaryStructure", 4 : "Position"})
    df = df[["Position", "NativeSecondaryStructure"]]
    df["Position"] = df["Position"].apply(pd.to_numeric)
    if not pathlib.Path(f'./results/{n_chain.upper()}/').exists():
        os.mkdir(pathlib.Path(f'./results/{n_chain.upper()}/'))
        with open(pathlib.Path(f'./results/{n_chain}/{n_chain.upper()}_conserved_summary.txt'), 'w') as f:
            f.write(f'')
    for file in path:
        p_file = (str(file).split('\\')[1])
        if p_file[0:5] == str(n_chain).upper()[0:5]:
            pan = pd.read_table(file)
            df_p = pd.DataFrame(pan)
            df_p = df_p.rename(columns={f"{str(df_p.columns[0])}": "value"})
            df_p = df_p.value.str.split(expand=True)
            df_p = df_p[df_p[0].str.contains("ASG")]
            df_p = df_p.rename(columns={6: "PredSecondaryStructure", 4 : "Position"})
            df_p = df_p[["Position", "PredSecondaryStructure"]]
            df_p["Position"] = df_p["Position"].apply(pd.to_numeric)
            df_join = df.set_index('Position').join(df_p.set_index('Position'), on="Position", how='left')
            print(p_file)
            df_join['Conservation'] = np.where(df_join['NativeSecondaryStructure']==df_join['PredSecondaryStructure'], True, False)
            count = int(df_join[df_join.Conservation == True].sum().apply(pd.Series).stack().tolist()[2])
            length = int(len(df_join))
            conserved = np.round(count/length*100, 2)
            print(f'Conserved: {conserved}%')
            with open(pathlib.Path(f'./results/{n_chain.upper()}/{n_chain.upper()}_conserved_summary.txt'), 'a') as f:
                f.write(f'{p_file} : {conserved}%\n')
            df_join.to_csv(pathlib.Path(f"./results/{n_chain.upper()}/{p_file.upper()}_conserved.csv"))

main()




