#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Implement the Symbolic Pattern Recognition (SPR) methods as published by:
  Akbilgic O and Howe J. Symbolic Pattern Recognition for Sequential Data. 
    Sequential Analysis. Accepted for Publication.
  Akbilgic, O., Howe, J. A., Davis, R. L., December 2016. Categorizing Atrial 
    Fibrillation via Symbolic Pattern Recognition. Journal of Medical Statistics 
    and Informatics 4 (8), 1–9.

Several optimizations have been used, including efficient hash-based substring
search and several recurrence relations between sequentially-sized lists of 
ngrams and pattern transition matrices.


Copyright (C) 2017 J. Andrew Howe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# FURTHER CHANCES FOR OPTIMIZATION?  more numpy?

import numpy as np
from HashSubstringSearch import *
from supportfuncs import *
import math

class SPRanal:
  """
  Container of all the important SPR-related attributes and methods.
  ---
  Attributes Are:
  alpha: list of the alphabet of symbols used in the analysis
  n_s: integer cardinality of the alphabet
  sequence: string of sequence data to analyze
  n: integer length of the sequence
  maxn_p: integer maximum size n_p of PTP matrices to generate
  t_np: float minimum sparsity index allowed to keep a PTP matrix
  hashP: a dict holding the hashing parameters x & p:
    p: prime integer sufficiently large to minimize the probability of collisions
    x: random integer in the inclusive range [0,p-1] for the polynomial
  n_p: integer length of the longest subsequence used in this SPR analysis
  PTPs: list of n_p "useful" PTP matrices
  ngrams: list of n_p lists of ngrams
  sparsity: nested list holding the sparsity table; sublists hold Observed counts, 
    Possible counts, and SI ratios by n_p, up to n_p
  ---
  Methods Are:
  BuildPTP: build a specified PTP matrix
  BuildPTPs: build optimal set of PTP matrices (Section 3.1)
  Distance: compute the distance between PTP matrices (Section 3.4)
  MakenGrams: generate ngrams
  Predict: predict the next symbol from a sequence (Section 3.2)
  PrintPTP: print a specified PTP matrix
  PrintiPTP: print a PTP matrix generated by BuildPTPs
  SetPTPParams: setup parameters to generate PTP matrices
  Simulate: simulate a similar sequence of symbols (Section 3.3)
  """
  def __init__(self,alpha,sequence):
    self.alpha = alpha
    self.n_s = len(alpha)
    self.sequence = sequence
    self.n = len(sequence)
    self.n_p = None
    self.maxn_p = None
    self.t_np = None
    self.hashP = {'p':None,'x':None}
    self.PTPset = False
    
  def __str__(self):
    mestr = '%r'%self
    if self.PTPset:
      for i in range(self.n_p):
        mestr += (self.PrintiPTP(i)+'\n')
    else:
      mestr += '\nBuildPTPs not run!'
    return mestr
  
  def __repr__(self):
    if (self.maxn_p is None):
      return "SPR Anal Object(SetPTPParams not run)\n\talpha(%d)=%r\n\tsequence(%d)=%r"\
      %(self.n_s,self.alpha,self.n,self.sequence)
    elif self.n_p is None:
       return "SPR Anal Object(BuildPTPs not run)\n\talpha(%d)=%r\n\tsequence(%d)=%r\n\tmax n_p=%d\n\tt_np=%0.4f\n\thash(p=%d,x=%d)"\
      %(self.n_s,self.alpha,self.n,self.sequence,self.maxn_p,self.t_np,self.hashP['p'],self.hashP['x'])     
    else:
      return "SPR Anal Object(n_p=%r)\n\talpha(%d)=%r\n\tsequence(%d)=%r\n\tmax n_p=%d\n\tt_np=%0.4f\n\thash(p=%d,x=%d)"\
      %(self.n_p,self.n_s,self.alpha,self.n,self.sequence,self.maxn_p,self.t_np,self.hashP['p'],self.hashP['x'])
  
  def SetPTPParams(self,maxn_p,t_np,hashP):
    self.maxn_p = maxn_p
    self.t_np = t_np
    try:
      _ = hashP['p']; _ = hashP['x']
    except AttributeError:
      raise AttributeError("hashP must be a dict with integer-valued keys 'p' and 'x'!")
    self.hashP = hashP
  
  def __SetPTP__(self,n_p,PTPs,ngrams,sparsities):
    self.n_p = n_p
    self.PTPs = PTPs
    self.ngrams = ngrams
    self.sparsities = sparsities
    self.PTPset = True

  def PrintiPTP(self,indx,hideMiss=False):
    """
    Print a nicely-formatted PTP matrix; 'nuff said.
    ---
    printStr = SPRanal.PrintiPTP(i,hideMIss=False)
    ---
    indx: integer index into PTPs [0,n_p) of the PTP to print
    hideMiss*: (False) optional boolean flag; if true, rows in the PTP matrix
    PTPstr: string that will print a nicely formatted PTP matrix
    ---
    JAH 20170619
    """

    # get the largest frequency, for formatting
    mxFreq = max(self.PTPs[indx][self.n_s])
    fmts = ['%%%dd'%(int(math.log10(mxFreq))+1)]*(self.n_s+1)
    
    # create the colunn heads and formatting strings
    colHds = self.alpha.copy(); colHds.append('Tot')
    if (len(self.PTPs[indx]) > self.n_s+1):
      # relFreq was on, so add alpha again
      colHds.extend(self.alpha)
      # and add the formats for freqs
      fmts.extend(['%0.4f']*self.n_s)
      
    data = np.array(self.PTPs[indx]).T
    
    # hide unobserved ngrams rows
    if hideMiss:
      # get the missing rows ...
      notMiss = [i for i,t in enumerate(self.PTPs[indx][self.n_s]) if t != 0]
      # ... and remove them
      data = data[notMiss,:]
      rowHds = [self.ngrams[indx][i] for i in notMiss]
    else:
      rowHds = self.ngrams[indx]
  
    return PrintTable(data,fmts,colHds,rowHds)
  
  def PrintPTP(self,PTP,ngrams,hideMiss=False):
    """
    Print a nicely-formatted PTP matrix; 'nuff said.
    ---
    printStr = SPRanal.PrintPTP(PTP,ngrams,hideMIss=False)
    ---
    PTP: specific PTP matrix that may have been built manually with BuildPTP
    ngrams: list of all ngrams of a specified length, should match with PTP
    hideMiss*: (False) optional boolean flag; if true, rows in the PTP matrix
      for unobserved ngrams are not printed
    PTPstr: string that will print a nicely formatted PTP matrix
    ---
    JAH 20170619
    """

    # get the largest frequency, for formatting
    mxFreq = max(PTP[self.n_s])
    fmts = ['%%%dd'%(int(math.log10(mxFreq))+1)]*(self.n_s+1)
    
    # create the colunn heads and formatting strings
    colHds = self.alpha.copy(); colHds.append('Tot')
    if (len(PTP) > self.n_s+1):
      # relFreq was on, so add alpha again
      colHds.extend(self.alpha)
      # and add the formats for freqs
      fmts.extend(['%0.4f']*self.n_s)
    
    data = np.array(PTP).T
    
    # hide unobserved ngrams rows
    if hideMiss:
      # get the missing rows ...
      notMiss = [i for i,t in enumerate(PTP[self.n_s]) if t != 0]
      # ... and remove them
      data = data[notMiss,:]
      rowHds = [ngrams[i] for i in notMiss]
    else:
      rowHds = ngrams
  
    return PrintTable(data,fmts,colHds,rowHds)  

  def Distance(self,otherSPR):
    """
    Compute the distance between two sequences, as measured by their individual
    sets of PTPs.  If either sequence has a higher n_s, the PTP of the other
    sequence is embedded in a larger matrix by being padded with 0's.  If either
    sequence has a nigher n_p, extra PTPs for the other sequence are created as
    zeros.
    ---
    diff = SPRanal.Distance(otherSPR)
    ---
    otherSPR: other sequence from which to compute the pairwise distance
    diff: the numeric distance between the two sequences
    ---
    JAH 20170621
    """
    
    # get the largest of the two n_s's and n_p's
    Ns = max(self.n_s,otherSPR.n_s)
    Np = max(self.n_p,otherSPR.n_p)
    
    # loop through all pairs of PTPs
    # note the implicit assumption that if one of the sequencies has a larger n_s,
    # that means that it has *extra* symbols *after* those of the other sequence
    diff = 0
    for n_p in range(Np):
      # first: get my PTP, only the probabilities
      try:
        mine = np.array(self.PTPs[n_p][(self.n_s+1):],dtype=float)
        # need to ensure it has enough rows & columns
        if (self.n_s < Ns):
          tmp = np.zeros((Ns,Ns**(n_p+1)),dtype=float)
          # embed this PTP in a larger PTP with 0-padding
          tmp[:mine.shape[0],:mine.shape[1]] = mine.copy(); mine = tmp
      except IndexError:
        # this one not found, so create a PTP of zeros
        mine = np.zeros((Ns,Ns**(n_p+1)),dtype=float)
      # second: get the other PTP, only the probabilities
      try:
        his = np.array(otherSPR.PTPs[n_p][(otherSPR.n_s+1):],dtype=float)
        # need to ensure it has enough rows & columns
        if (otherSPR.n_s < Ns):
          tmp = np.zeros((Ns,Ns**(n_p+1)),dtype=float)
          # embed this PTP in a larger PTP with 0-padding
          tmp[:his.shape[0],:his.shape[1]] = his.copy(); his = tmp
      except IndexError:
        # this one not found, so create a PTP of zeros
        his = np.zeros((Ns,Ns**(n_p+1)),dtype=float)    
      # third: compute the sum of absolute differences
      diff += np.sum(np.abs(his - mine))
    
    return diff

  def Simulate(self,nstar):
    """
    Use the conditional probabilities in the PTP matrices to simulate sequences
    with similar pattern transition behavior as in the original sequence. This 
    uses the Predict function to compute the probabilities.
    ---
    simulation = SPRanal.Simulate(nstar)
    ---
    nstar: integer desired length of the simulated sequence
    simulate: string simulated sequence
    ---
    JAH 20170621
    """
    
    # generate up front all the random variates needed
    rnds = np.random.rand(nstar)
    simRng = range(self.n_s)
    # setup the one-symbol simulator lambda function  
    simOne = lambda rnd,prbs: [self.alpha[i] for i,p in zip(simRng,(rnd <= prbs)) if p][0]
    
    # predict the next symbol to start off the simulation
    alphaProbs = self.Predict()[1]
    Sstar = simOne(rnds[0],np.cumsum(alphaProbs))
    
    # to be more efficient, we'll save every list of alphaProbs we see, keyed
    # to the subsequence which generated it
    subSeqs = dict()
    
    # now loop through and generate each new simulated symbol, each time using
    # a PTP of bigger i, up to a max of n_p
    for i in range(1,nstar):
      subSeq = Sstar[-min(i,self.n_p):]
      try:
        alphaProbs = subSeqs[subSeq]
      except KeyError:
        # didn't see this subsequence before, so generate then save it
        alphaProbs = self.Predict(subSeq)[1]
        subSeqs[subSeq] = alphaProbs
      Sstar += simOne(rnds[i],np.cumsum(alphaProbs))
  
    return Sstar

  def Predict(self,predStart = None):
    """
    Use the conditional probabilities in the PTP matrices to predict the next
    symbol from sequence, given the most recent n_p symbols.  The probabilities
    from all PTP matrices are weighted evenly.
    ---
    (prediction,probabilities) = SPRanal.Predict(predStart=None)
    ---
    predStart*: (None) optional list of sequence end; if passed, this is used
      to predict the next symbol; otherwise, the last n_p symbols of the 
      sequence is used
    prediction: the predicted next symbol
    probabilities: list of probabilities for each symbol in the alphabet, conditional
      upon the sequence
    ---
    JAH 20170621
    """
    
    # generate the ending point 
    if predStart is None:
      predStart = self.sequence[-self.n_p:]
      w = self.n_p
    else:
      w = min(len(predStart),self.n_p)
    
    # loop through the PTP matrices to get the conditional probabilities
    alphaProbs = []
    for i in range(w):
      # get the last i symbols from the sequence ...
      seqEnd = predStart[-(i+1):]
      # then find in the appropriate ngram ...
      nxtRow = self.ngrams[i].index(seqEnd)
      # then get the appropriate row from the appropriate PTP
      alphaProbs.append([p[nxtRow] for p in self.PTPs[i][self.n_s+1:]])
      # if this row is entirely blank, subtract 1 for this PTP from w
      w -= (self.PTPs[i][self.n_s][nxtRow] == 0)
    # now that all the probs have been gathered, compute the weighted average
    alphaProbs = [sum(i)/w for i in zip(*alphaProbs)]
    
    # finally, return the prediction and also all the probabilities
    return self.alpha[alphaProbs.index(max(alphaProbs))],alphaProbs

  def BuildPTPs(self,talk=False):
    """
    Sequentially build a list of "useful" PTP matrices by computing the ratio of 
    number unique observed patterns (non-0 rows in PTP) in each PTP matrix to the
    number of possible patterns. This ratio is called the sparsity index (SI), and
    this procedure stops computing PTP matrices once the SI drops below a specific
    threshold. In fact, it only computes PTPs that are guaranteed to not be too
    sparse, because the number of observed patterns for PTP_i comes from computing
    PTP_{i-1}.
    ---
    usage: SPRanal.BuildPTPs(talk=False)
    ---
    talk*: (false) optional boolean flag if True, print a nice sparsity table 
    ---
    JAH 20170620
    """
    
    # make list of lists of ngrams
    ngramS = self.MakenGrams()
    
    # sparsTities table: [Observed,Expected,Sparsity]; yes the typo is intended :-)
    sparsTities = [[0]*self.maxn_p]
    sparsTities.append([self.n_s**i for i in range(1,self.maxn_p+1)])
    sparsTities.append([0]*self.maxn_p)
  
    ''' Note this all works because the found patterns from computing PTP_i
    is *almost* the observed for PTP_{i+1} '''
    
    # the list of observeds for n_p=1 is just the list of unique values
    fnd_ip1 = np.unique(list(self.sequence)).tolist()
   
    # loop through PTPs up to maxn_p until SI < t_np
    PTPs = []
    for i in range(0,self.maxn_p):
      # compute the sparsity for PTP_{i}, using found patterns from PTP_{i-1}
      # to get the observed, strip off the last elements of the found patterns
      # and unique the list (How do you catch a unique cat? Unique up on him!)
      sparsTities[0][i] = np.unique([i[:-1] for i in fnd_ip1]).size
      sparsTities[2][i] = sparsTities[0][i]/sparsTities[1][i]
      # can we exit early?
      if (sparsTities[2][i] < self.t_np):
        break
      # build the PTP_i matrix
      (PTP_i,fnd_ip1) = self.BuildPTP(ngramS[i],ngramsRed=fnd_ip1)
      PTPs.append(PTP_i)
    # final increment i to maxn_p iff all PTPs passed
    i += (sparsTities[2][i] >= self.t_np)
    
    # print a nicely-formatted table of sparsities, if requested
    if talk:
        print(PrintTable(np.array(sparsTities).T[:i,:],['%d','%d','%0.4f'],\
        ['Obs','Poss','SI'],[str(i) for i in range(1,i+1)]))
    
    # set the list of PTPs, the ngrams, and the truncated sparsities table
    self.__SetPTP__(i,PTPs,ngramS[:i],[col[:i] for col in sparsTities])

  def MakenGrams(self,maxn_p=None,only=False):
    """
    For a specified alphabet, return lists of ngrams up to a max length of maxn_p.
    Optionally, return a list of ngrams of only the specified n_p.  This works by
    using a set of reccurrence relations for a) the pattern between the columns
    in each set of ngrams, and b) between each set of ngrams.
    ---
    usage: ngrams = SPRanal.MakenGrams(maxn_p=None,only=False)
    ---
    maxn_p*: (None) optional value for maxn_p; if None, comes from the parent
    only*: (False) optional boolean flag if set to True, only create the list
    of n_p-grams
    ngrams: list of maxn_p lists of ngrams; if only = True, list of n_p ngrams
    ---
    JAH 20170619
    """
    
    if (maxn_p is None):
      maxn_p = self.maxn_p
    
    # if the only flag is True, just do the specified n_p
    if only:
      ngrams = []
      for cnt in range(maxn_p):
        # number times to repeat each letter *in the subsequence*
        letrepts = self.n_s**cnt
        # number times to repeat the subsequences
        arrrepts = self.n_s**(maxn_p - 1 - cnt)    
        # build the subsequence and sort
        tmp = self.alpha*letrepts; tmp.sort() # this uses Timsort, which is state of the art
        # repeat the subsequences & append
        ngrams.append((tmp)*arrrepts) 
      # join across lists in this set of ngrams, and also
      # reverse the columns order so the patterns are lexicographically sorted
      ngrams = [''.join(i) for i in zip(*ngrams[::-1])]
    else:
      ngrams = []
      thisngrams = []
      # build the largest ngram first
      for cnt in range(maxn_p):
        # number times to repeat each letter *in the subsequence*
        letrepts = self.n_s**cnt
        # number times to repeat the subsequences
        arrrepts = self.n_s**(maxn_p - 1 - cnt)    
        # build the subsequence and sort
        tmp = self.alpha*letrepts; tmp.sort() # this uses Timsort, which is state of the art
        # repeat the subsequences & append
        thisngrams.append((tmp)*arrrepts) 
      # join across lists in this set of ngrams, and also
      # reverse the columns order so the patterns are lexicographically sorted
      ngrams.append([''.join(i) for i in zip(*thisngrams[::-1])])
      # now sequentially tear down the largest set of ngrams to build the others
      # this uses the recurrence relation (ng_i = ng_i+1}[:alpha*i,:-1])
      for cnt in range(maxn_p-1,1,-1):
        # remove the last column, then in each column just keep the first elements
        thisngrams = [col[:(self.n_s**cnt)] for col in thisngrams[:-1]]
        # join columns, reverse, and save in ngrams
        ngrams.append([''.join(i) for i in zip(*thisngrams[::-1])])
      # now add directly the 1st ngram
      ngrams.append(self.alpha)
    
    if only:
      return ngrams
    else:
      return ngrams[::-1]

  def BuildPTP(self,ngrams,ngramsRed=None):    
    """
    Use an optimized Rabin-Karp hash search algorithm to build the complete pattern
    transition matrix for a specific length i=n_p. The symbols in the search string
    should be limited to the alphabet used to generate the ngrams. This algorithm
    can take advantage of the recurrence relation that PTP_{i+1} can not have any
    rows which are built from following patterns not found for PTP_i. To do so, 
    pass as ngramsRed the fndPatterns output from PTP_i.
    ---
    usage: (PTP,fndPatterns) = SPRanal.BuildPTP(ngrams,ngramsRed=None)
    ---
    ngrams: list of n_p-grams from which to build the PTP matrix
    ngramsred: reduced list of n_p-grams that are supposedly known to exist in
      the sequence
    PTP: the complete nested list of pattern transition frequencies, with a row
      for each ngram, a column for the following frequency for each symbol in
      the alphabet, followed by a total column, followed by columns of relative
      frequencies
    fndPatterns: list of actual found patterns, which can be passed in to this
      function to more quickly build the PTP matrix for the next higher n_p
    ---
    JAH 20170619
    """
    
    # pre-build the first half of the PTP matrix
    PTP = [[0]*len(ngrams) for _ in self.alpha]
  
    # more lengths
    n_p = len(ngrams[0])
    
    # set the list of search items as appropriate
    # must also build a list of indices of the reduced list into the ngrams list
    if (ngramsRed == None):
      searchMe = ngrams
      ngramsInd = range(len(ngrams))
    else:
      searchMe = ngramsRed
      ngramsInd = [ngrams.index(i) for i in ngramsRed]
    
    # loop through each ngram and do the searching
    fndPatts = []
    for i,ngram in zip(ngramsInd,searchMe):
      # get all the starting indices    
      indxs = HashSearch(self.sequence,ngram,self.hashP['p'],self.hashP['x'])
      # get all the following chars
      chars = [self.sequence[i+n_p] for i in indxs if i+n_p+1 <= self.n]
      # compute the frequencies
      freqs = np.unique(chars,return_counts=True)
      # now must loop through the alphabet to get the full tabulation :-(
      if (len(freqs[0]) != 0):
        for j,alph in enumerate(self.alpha):
          try:
            PTP[j][i] = freqs[1][freqs[0]==alph][0]
          except IndexError:
            # if this symbol is not in the tabulation, do nothing
            pass
        # store the actual found patterns, which can be used for the next higher PTP
        for alph in freqs[0]:
          fndPatts.append(ngram+alph)
  
    # now create the totals
    tots = [sum(i) for i in zip(*PTP)]
    PTP.append(tots)
    # finally, generate the relative frequencies
    rel = []
    for col in PTP[:-1]:
      rel.append([i/t if t != 0 else 0.0 for i,t in zip(col,tots)])
    PTP.extend(rel)
  
    # return the final full PTP matrix
    return PTP, fndPatts

if (__name__ == "__main__"):
  '''
  SPR Analysis Demo Code, using same example as in the original article
  '''
  # create the SPR analysis object
  thisSPR = SPRanal(['a','b','c'],'aabcabccbabcabcbaabc')
  print(thisSPR)
  # set it up for the modeling - this must be done before anything else
  # from Section 3.1 Learning Pattern Transition Behaviour of the original article
  thisSPR.SetPTPParams(10,0.1,{'p':4241,'x':42})
  print(thisSPR)
  
  # functions (used by BuildPTPs) to generate specified ngrams and PTP matrices
  ngrams_2 = thisSPR.MakenGrams(maxn_p=2,only=True)
  PTP_2 = thisSPR.BuildPTP(ngrams_2,ngramsRed=None)[0]
  print(thisSPR.PrintPTP(PTP_2,ngrams_2,True))
  
  # identify the optimal n_p and set the PTP matrices 
  thisSPR.BuildPTPs(True)
  print(thisSPR.PrintiPTP(1))
  
  # predict the next symbol, and simulate a similar sequence; these are from sections
  # 3.2 SPR for Prediction and 3.3 Simulating with SPR, respectively
  print('The next symbol should be: %s'%thisSPR.Predict(predStart=None)[0])
  print('A similar sequence is: %s'%thisSPR.Simulate(20))
  
  # compute the distances between some sequences; these are from section
  # 3.4 Clustering with SPR
  SstarSPR = SPRanal(thisSPR.alpha,'abcbaabcabccbabcabcb')
  SstarSPR.SetPTPParams(10,0.1,{'p':4241,'x':42})
  SstarSPR.BuildPTPs(True)
  
  SstarstarSPR = SPRanal(thisSPR.alpha,'bcbabcbaababcbababcc')
  SstarstarSPR.SetPTPParams(10,0.1,{'p':4241,'x':42})
  SstarstarSPR.BuildPTPs(True)
  print('dist(S,S*) = %0.2f'%thisSPR.Distance(SstarSPR))
  print('dist(S,S**) = %0.2f'%thisSPR.Distance(SstarstarSPR))
  print('dist(S*,S**) = %0.2f'%SstarSPR.Distance(SstarstarSPR))
