#################################################
# huanchen 09/2016
#################################################

import sys
import os
from random import shuffle

dataFileDir = './Datafiles'
outputFile_random = 'bulkload_random'
outputFile_sort = 'bulkload_sort'

wordList = []

for dirName, subdirList, fileList in os.walk(dataFileDir) :
    for fname in fileList :
        f = open(dataFileDir + '/' + fname, 'r')
        for line in f :
            wordList.append(line[0:-1])

##################################################

shuffle(wordList)

f_out_random = open(outputFile_random, 'w')
for word in wordList :
    f_out_random.write(word)
    f_out_random.write('\n')

##################################################

wordList.sort()

f_out_sort = open(outputFile_sort, 'w')
for word in wordList :
    f_out_sort.write(word)
    f_out_sort.write('\n')
