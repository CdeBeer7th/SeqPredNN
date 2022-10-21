import sklearn.metrics as metrics
import torch
from torch import nn
from neural_net import StructureDataset, NeuralNetwork
import pathlib
import argparse
from torch.utils.data import DataLoader
import numpy as np
from plots import Plots
import warnings

classes = {'GLY': 'G', 'ALA': 'A', 'CYS': 'C', 'PRO': 'P', 'VAL': 'V', 'ILE': 'I', 'LEU': 'L', 'MET': 'M', 'PHE': 'F',
           'TRP': 'W', 'SER': 'S', 'THR': 'T', 'ASN': 'N', 'GLN': 'Q', 'TYR': 'Y', 'ASP': 'D', 'GLU': 'E', 'HIS': 'H',
           'LYS': 'K', 'ARG': 'R'}
device = "cuda" if torch.cuda.is_available() else "cpu"


def get_args():
    arg_parser = argparse.ArgumentParser(description="predict sequences from protein conformational features and test "
                                                     "model performance")
    arg_parser.add_argument('feature_dir', type=str, help="directory of processed chain features")
    arg_parser.add_argument('test_list', type=str, help="path to list of protein chain code for sequence prediction")
    arg_parser.add_argument('model_params', type=str, help="file containing trained model parameters")
    arg_parser.add_argument('-n', '--nth_prediction', type=int, default=1,
                            help="nth predicted residue for each position output")
    arg_parser.add_argument('-t', '--threshold', type=float, default=0,
                            help="softmax threshold limit in range (0,1]")
    arg_parser.add_argument('-p', '--pred_only', action='store_true',
                            help="only predict sequences, without testing the model and comparing predictions with "
                                 "true sequences.")
    arg_parser.add_argument('-o', '--out_dir', type=str, default='./pred',
                            help="output directory. Will create a new directory if OUT_DIR does not exist.")
    args = arg_parser.parse_args()
    return pathlib.Path(args.feature_dir), pathlib.Path(args.test_list), pathlib.Path(args.model_params), \
           pathlib.Path(args.out_dir), args.pred_only, args.nth_prediction, args.threshold


class Predictor:
    def __init__(self, parameter_path, pred_only, nth_prediction, threshold):
        self.model = NeuralNetwork(input_nodes=180).to(device)
        parameters = torch.load(parameter_path)
        self.model.load_state_dict(parameters)
        self.pred_only = pred_only
        # set variable to argument. If not exists set to highest probability
        if not nth_prediction:
            self.nth_prediction = 1
        else:
            self.nth_prediction = nth_prediction
        if not threshold:
            self.threshold = 0
        else:
            self.threshold = threshold
            print(threshold)

    # set up dataloader for the structural features of the chain
    @staticmethod
    def load_features(feature_paths):
        feature_dict = {key: torch.tensor(torch.load(path), dtype=torch.float) for path, key in
                        zip(feature_paths, ['displacements', 'residue_labels', 'rotations', 'torsional_angles'])}
        dataset = StructureDataset(feature_dict)
        dataloader = DataLoader(dataset, shuffle=False)
        return dataloader

    # predict the amino acid class of each residue in the chain
    def sequence(self, feature_paths):
        dataloader = self.load_features(feature_paths)
        self.model.eval()
        chain_softmax = []
        pred_residues = []
        true_residues = []
        chain_loss = []
        # load residue features one at a time
        for inputs, label in dataloader:
            with torch.no_grad():
                # predict residue
                output = self.model(inputs.to(device))
                if not self.pred_only:
                    loss_fn = nn.CrossEntropyLoss()
                    loss = loss_fn(output, label.to(device)).item()
                    chain_loss.append(loss)
                    true_residues.extend(label.cpu().numpy())
            softmax = nn.functional.softmax(output, dim=1)
            chain_softmax.extend(softmax.cpu().numpy())

            # the output node with the highest value
            top_residue = output.argmax(1)
            print(int(top_residue))
            print(float(torch.kthvalue(softmax, 20)[0]))
            # if top node softmax probability is greater than threshold then choose that node
            if float(torch.kthvalue(softmax, 20)[0]) > self.threshold:
                print(f"top: {int(top_residue)}")
                pred_residues.append(int(top_residue))
            else:
                nth_residue = torch.kthvalue(output, 21 - self.nth_prediction)[1]
                print(f"nth: {int(nth_residue)}")
                pred_residues.append(int(nth_residue))
        return pred_residues, chain_softmax, chain_loss, true_residues

    # generate sequence string for the residue and add residues that were excluded during featurisation
    def complete_seq(self, pred_residues, true_residues, chain, feat_dir):
        excluded_res_path = feat_dir / ('excluded_residues_' + chain + '.csv')
        excluded_residues = {}
        pred_seq = ''
        true_seq = ''
        # read list of excluded residues, if any residues were excluded
        if excluded_res_path.exists():
            with open(excluded_res_path, 'r') as file:
                # excluded residues written in file as index,residue_name
                for line in file:
                    line = line.split(',')
                    excluded_residues[int(line[0])] = line[1].strip('\n')
        j = 0
        for i in range(len(list(excluded_residues)) + len(pred_residues)):
            # predict 'X' for all excluded residues
            if i in excluded_residues:
                pred_seq += 'X'
                if not self.pred_only:
                    # true residues are only 'X' if they are non-standard residues
                    if excluded_residues[i] in list(classes):
                        true_seq += classes[excluded_residues[i]]
                    else:
                        true_seq += 'X'
            else:
                pred_seq += list(classes.values())[int(pred_residues[j])]
                if not self.pred_only:
                    true_seq += list(classes.values())[int(true_residues[j])]
                j += 1
        return pred_seq, true_seq


class Evaluator:
    def __init__(self, out_dir, nth_prediction, threshold):
        self.out_dir = out_dir
        self.model_predictions = []
        self.model_true = []
        self.model_softmax = []
        self.model_loss = []
        self.nth_prediction = nth_prediction
        self.threshold = threshold

    @staticmethod
    def check_labels(true_residues):
        unused_residues = []
        labels = []
        for key in range(0, 20):
            if key not in true_residues:
                unused_residues.append(key)
            else:
                labels.append(key)
        return unused_residues, labels

    def write_report(self, file, chain_report, avg_loss, unused_residues):
        file.writelines(chain_report)
        file.write('\nAverage loss: ' + str(avg_loss))
        file.write('\nNote: precision and F-scores are set to 0.0 for classes that have no predictions')
        if unused_residues:
            unused = ''
            for res in unused_residues:
                unused += list(classes)[res] + ', '
            unused.rstrip(', ')
            file.write('Residues with 0 support: ' + unused)

    # generate a classification report and confusion matrices for the chain
    def chain(self, chain, true_seq, true_residues, pred_residues, loss, chain_softmax):
        self.model_predictions.extend(pred_residues)
        self.model_true.extend(true_residues)
        self.model_softmax.extend(chain_softmax)
        self.model_loss.extend(loss)
        avg_loss = np.mean(loss)

        # list residues that do and do not occur in the true sequence
        unused_residues, labels = self.check_labels(true_residues)
        # only plot confusion matrices if all 20 residues occur in the label set
        with warnings.catch_warnings():
            # suppress sklearn warnings
            warnings.simplefilter("ignore")
            # generate report of per-class precision, recall and F1-scores
            chain_report = metrics.classification_report(true_residues, pred_residues, target_names=list(classes),
                                                         labels=labels, digits=3, zero_division=0)
        # write files
        with open(self.out_dir / chain / f"report.txt", 'w') as file:
            self.write_report(file, chain_report, avg_loss, unused_residues)
        with open(self.out_dir / chain / 'original_sequence.txt', 'w') as file:
            file.write(true_seq)
        np.savetxt(self.out_dir / chain / 'probabilities.csv', chain_softmax, delimiter=',')
        np.savetxt(self.out_dir / chain / 'residue_losses.csv', loss, delimiter=',')

    # generate a classification report, confusion matrices and a top-K accuracy curve for the test set
    def model(self):
        model_plot = Plots(self.out_dir)
        avg_loss = np.mean(self.model_loss)

        # list residue labels that do and do not occur in the test set
        unused_residues, labels = self.check_labels(self.model_true)
        # only plot confusion matrices if all 20 residues occur in the label set
        if not unused_residues:
            model_plot.confusion_matrix(self.model_true, self.model_predictions, None, 'unnormalised_conf_matrix.png')
            model_plot.confusion_matrix(self.model_true, self.model_predictions, 'pred', 'pred_norm_conf_matrix.png')
            model_plot.confusion_matrix(self.model_true, self.model_predictions, 'true', 'true_norm_conf_matrix.png')
            with warnings.catch_warnings():
                # suppress sklearn warnings
                warnings.simplefilter("ignore")
                top_k_accuracy = {k: metrics.top_k_accuracy_score(self.model_true, self.model_softmax, k=k) for k in
                                  range(1, 21)}
            with open(self.out_dir / 'top_K.txt', 'w') as file:
                for k in top_k_accuracy:
                    file.write(str(k) + ': ' + str(top_k_accuracy[k]) + '\n')
        else:
            print("Could not plot confusion matrices or top-K accuracy curve because some residues do not have any "
                  "labels in the test set")
        with warnings.catch_warnings():
            # suppress sklearn warnings
            warnings.simplefilter("ignore")
            # generate report of per-class precision, recall and F1-scores
            model_report = metrics.classification_report(self.model_true, self.model_predictions,
                                                         target_names=list(classes), digits=3, zero_division=0,
                                                         labels=labels)

        with open(self.out_dir / 'report.txt', 'w') as file:
            self.write_report(file, model_report, avg_loss, unused_residues)


def read_test_list(test_list):
    with open(test_list, 'r') as file:
        test_chains = [line.split(' ')[0].strip('\n') for line in file]
        if test_chains[0] == 'PDBchain':
            test_chains = test_chains[1:]
    return test_chains


def main():
    feat_dir, test_list, parameter_path, out_dir, pred_only, nth_prediction, threshold = get_args()
    print(get_args())
    if not feat_dir.exists():
        raise FileNotFoundError(feat_dir)
    if not out_dir.exists():
        out_dir.mkdir()

    test_chains = read_test_list(test_list)
    print(pred_only)
    predict = Predictor(parameter_path, pred_only, nth_prediction, threshold)
    evaluate = Evaluator(out_dir, nth_prediction, threshold)

    n_chains = len(test_chains)
    i = 1
    for chain in test_chains:
        print('Chain', str(i) + '/' + str(n_chains))
        feature_paths = [feat_dir / (feature + chain + '.pt') for feature in
                         ['displacements_', 'residue_labels_', 'rotations_', 'torsional_angles_']]
        if all([file.exists() for file in feature_paths]):
            try:
                # run the model on each residue in the chain
                pred_residues, chain_softmax, loss, true_residues = predict.sequence(feature_paths)

                # convert true and predicted residue lists to strings, with X for non-standard residues
                pred_seq, true_seq = predict.complete_seq(pred_residues, true_residues, chain, feat_dir)
                print(chain, '- Predicted sequence:\n' + pred_seq)
                if not pred_only:
                    print(chain, '- Original sequence:\n' + true_seq + '\n')

                chain_dir = out_dir / chain
                if not chain_dir.exists():
                    chain_dir.mkdir()
                with open(chain_dir / f"top_{nth_prediction}_{int(threshold*100)}%_threshold_prediction.txt", 'w') as file:
                    file.write(pred_seq)

                if not pred_only:
                    # generate a classification report and confusion matrices for the chain
                    evaluate.chain(chain, true_seq, true_residues, pred_residues, loss, chain_softmax)

                i += 1
            except Exception as error:
                warning = str(str(type(error)) + ': ' + str(error) + ' in chain ' + chain)
                warnings.warn(warning, UserWarning)
                with open(out_dir / 'excluded.txt', 'a') as file:
                    file.write(chain + '\n')
                n_chains -= 1
        else:
            print('Excluded chain', chain, 'due to missing feature files.')
            with open(out_dir / 'excluded.txt', 'a') as file:
                file.write(chain + '\n')
            n_chains -= 1

    if not pred_only:
        # generate a classification report, confusion matrices and a top-K accuracy curve for the entire test set
        evaluate.model()


main()
