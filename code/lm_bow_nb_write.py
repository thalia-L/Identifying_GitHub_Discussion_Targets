import argparse, hashlib, csv, random
import numpy as np
import collections

from format_lm_input import create_committer_data_dict, create_comments_dict, \
                            train_test_split, get_index_tokenizer, build_data, \
                            trim_pad_sequences, flatten_comments_dict, mention_preprocess,\
                            remove_short_comments, Using_one_project, closed_class_only,\
                            remove_closed_class, remove_non_committer

from format_lm_input import COMMIT_METRICS

from keras.models import Model, model_from_json, Sequential
from keras.layers.embeddings import Embedding
from keras.layers import Input, LSTM, Dense
from keras.layers.convolutional import Conv1D
from keras.layers.pooling import MaxPooling1D
from keras.layers.core import Flatten
from keras.callbacks import Callback
from sklearn.metrics import roc_auc_score, confusion_matrix, r2_score
from sklearn.naive_bayes import MultinomialNB

from util import load_cached_data, get_cache_path

MODEL_TYPES = ['speaking', 'spoken_to']
VOCAB_SIZE = 15000
RESULT_FILE = 'nb_result'

if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Formats data for LM input')
    argparser.add_argument('--base_comment_dir',
                           action='store',
                           help='Base directory of issue comments.',
                           default='../data/sample_46_projs_issues')
    argparser.add_argument('--base_commit_dir',
                           action='store',
                           help='Base directory of commits.',
                           default='../data/sample_46_projs_commits')
    argparser.add_argument('--comments_file',
                           action='store',
                           help='Comments file name.',
                           default='issue_comments_REPLACECODE.csv')
    argparser.add_argument('--model_type',
                           action='store',
                           help='Model type.',
                           choices=MODEL_TYPES,
                           default='speaking')
    argparser.add_argument('--top_perc',
                           action='store',
                           help='Top percent of the response metric to be the \
                           positive class.',
                           type=int,
                           default=10)
    argparser.add_argument('--metric',
                           action='store',
                           help='Metric for the top percent.',
                           choices=COMMIT_METRICS,
                           type=str,
                           default='commits')
    argparser.add_argument('--cross_project',
                           action='store',
                           help='Test on this project and train on all others',
                           type=int,
                           default=-1)
    argparser.add_argument('--vocab_size',
                           action='store',
                           help='Max vocab size to consider. Default is 15,000',
                           type=int,
                           default=10000)
    argparser.add_argument('--only_committer',
                           action='store',
                           help='If only use data from committers.',
                           type=int,
                           default=0)
    argparser.add_argument('--noise_len',
                           action='store',
                           help='Post has less than this number of token is \
                           considered noise and will be removed.',
                           type=int,
                           default=5)

    args = argparser.parse_args()

    print('model type: ' + args.model_type + '\n')

    # read in and cache committer and comments data
    committer_dict = create_committer_data_dict(args.base_commit_dir, 
        args.top_perc, args.metric)
    h = hashlib.sha1()
    h_name = 'language_status.py' + args.base_comment_dir + args.comments_file
    h.update(h_name.encode('utf-8'))
    comments_dict = create_comments_dict(args.base_comment_dir, committer_dict,
        args.comments_file, args.model_type, h)

    print('Removing noise')
    comments_dict = remove_short_comments(comments_dict, args.noise_len)

    print('Removing non-committers')
    if args.only_committer:
      comments_dict = remove_non_committer(comments_dict, committer_dict, args.model_type)

    print('Splitting idxs')
    train_idxs, test_idxs = train_test_split(comments_dict, args.cross_project)
    tkr = get_index_tokenizer(comments_dict, train_idxs, args.vocab_size)

    print('Building data')
    X, y, ids = build_data(comments_dict, committer_dict, tkr, args.model_type)

    print('Converting texts to sequences')
    X = tkr.texts_to_matrix(X, mode='count')

    X_train = [X[i] for i in train_idxs]
    y_train = [y[i] for i in train_idxs]
    X_test = [X[i] for i in test_idxs]
    y_test = [y[i] for i in test_idxs]

    clf = MultinomialNB()
    clf.fit(X_train, y_train)
    print("accuracy:")
    print(clf.score(X_test, y_test))
    y_test_prob = clf.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, y_test_prob))
    print("auc:")
    print(auc)


    
    


        
