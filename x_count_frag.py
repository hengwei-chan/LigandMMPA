#!/usr/bin/env python3

import sys
import re
import gc
import time
import json
import pickle
import gzip,bz2
import itertools
import pandas as pd
from tqdm import tqdm
from pathos import multiprocessing
from argparse import ArgumentParser
chunk = 500     # mpi chunk size


def main():

  args = UserInput()

  with open(args.f_list, 'r') as fi:
    infile = list(filter(None, (l.rstrip() for l in fi)))   # remove empty lines
  print(infile)

  Temp = [ ProcessFrag(f) for f in infile ]
  r_df = pd.DataFrame(list( set(tuple(itertools.chain.from_iterable(Temp)))),
            columns=['r_group','smiles','atom_num'] ).sort_values(['atom_num'])

  print('## number of unique frag: ', len(r_df))

############################################################
def read_in_json( x ):
  y = json.loads(x)
  z = []

  if not re.search('IGNORE', y[0]):
    try:
      for i in y[5]:
        # if json[5][i][8] has separate frags, [9] will be 'null' and return None
        # also remove any radical and cations
        if i[9] is not None and not re.search(r'\[CH\]|\[CH2\]|\[CH2\+\]', i[8]):
          z.append( (i[8], i[9], i[6]) )
      return z

    except IndexError:
      print(y)

########################################################
## process the json formatted fragment library and select fragments with criteria
def ProcessFrag( f ):

  with file_handle(f) as fi:
    Tmp = [l.rstrip() for l in fi]
  Frags = Tmp[10:]    # remove first 10 lines, which are just file formatting
  del Tmp

  mpi = multiprocessing.Pool(processes=multiprocessing.cpu_count())

  start = time.perf_counter()
#  Tmp = [frag(x) for x in tqdm(Frags, total=len(Frags))]
  Tmp = [x for x in tqdm(mpi.imap(read_in_json, Frags, chunk),total=len(Frags))]
  mpi.close()
  mpi.join()
  end = time.perf_counter()
  print((end-start)/1000, 'ms')

  Tmp2 = [frag for frag in Tmp if frag is not None]
  Tmp3 = list(itertools.chain.from_iterable(Tmp2))    # flatten nested lists
  FgSele = list(set(tuple(Tmp3)))                     # select unique smiles

  del Tmp
  del Tmp2
  del Tmp3
  del Frags
  gc.collect()

  return FgSele

##########################################################################
def file_handle(file_name):
  if re.search(r'.gz$', file_name):
    return gzip.open(file_name, 'r')
  elif re.search(r'.bz2$', file_name):
    return bz2.BZ2File(file_name, 'r')
  else:
    return open(file_name, 'r')

##########################################################################
def UserInput():
  p = ArgumentParser(description='Command Line Arguments')

  p.add_argument('-list', dest='f_list', required=True,
                 help='List of Smiles fragmentation files')

  args=p.parse_args()
  return args


##########################################################################
if __name__ == '__main__':
  main()

##########################################################################
#
#   Peter M.U. Ung @ MSSM/Yale
#
#   v1.0   19.05.15
#
#   count how many fragments are in a list of JSON files generated by 
#   mmpDB fragmentation.
#
#

