#!/usr/bin/env python
##################################################
# File Name: consensus.py
# Author: Rui
# mail: rdong1989@gmail.com
# Created Time: Thu 11 Jul 2019 03:08:59 PM EDT
################################################

from collections import defaultdict
import anndata
import scanpy as sc
import numpy as np
from sklearn.cluster import KMeans

def calMPG(funcGiniClust,funcMinpts):
    funcGiniDict={}
    for i in range(0,len(funcGiniClust)):
        funcGiniDict[funcGiniClust[i]]=funcGiniDict.get(funcGiniClust[i],0) + 1
    s=0.49*(funcMinpts/len(funcGiniClust))
    m=(funcMinpts/len(funcGiniClust))*4
    funcRare=[]
    for keys in funcGiniDict.keys():
        funcGiniDict[keys]=funcGiniDict[keys]/len(funcGiniClust)
        if (funcGiniDict[keys]<m):
            funcRare.append(keys)
        funcGiniDict[keys]=1-1/(1 + np.exp(-(funcGiniDict[keys]-m)/s))
    return(funcGiniDict)

def calMtilde(funcNormGiniClust,funcGiniClust,funcFanoClust,simMtilde):
    for i in range(0,funcGiniClust.shape[0]):
        for j in range(0,funcGiniClust.shape[0]):
            if (i!=j):
                if funcGiniClust[i]==funcGiniClust[j]:
                    MPG=1
                else:
                    MPG=0
                if funcFanoClust[i]==funcFanoClust[j]:
                    MPF=1
                else:
                    MPF=0
                GWeights=max(funcNormGiniClust[i],funcNormGiniClust[j])
                normG=GWeights/(GWeights+0.1)
                simMtilde[i][j]=MPG*normG+MPF*(1-normG)
            else:
                simMtilde[i][j]=1

def determinK(gini,fano):
    count=0
    for g in gini.keys():
        if (g=="0"):
            continue
        for f in fano.keys():
            overlap=len(np.intersect1d(gini[g],fano[f]))
            overlapG=overlap/len(gini[g])
            overlapF=overlap/len(fano[f])
            if (overlapG>=0.8 and overlapF>=0.8):
                count+=1
    k=len(gini)+len(fano)-count-1
    return(k)

def overlapGF(gini,fano,giniList):
    giniNoOverlap={}
    for g in gini.keys():
        giniNoOverlap[int(g)]=int(g)
        if (g==0):
            continue
        for f in fano.keys():
            overlap=len(np.intersect1d(gini[g],fano[f]))
            overlapG=overlap/len(gini[g])
            overlapF=overlap/len(fano[f])
            if (overlapG>=0.8 and overlapF>=0.8):
                giniNoOverlap[int(g)]=0
    for i in range(len(giniList)):
        giniList[i]=giniNoOverlap[giniList[i]]
    return(giniList)

def generateMtilde(GCconsensus):
    giniCluster=GCconsensus['giniCluster']
    fanoCluster=GCconsensus['fanoCluster']
    count=1
    giniCellDict = defaultdict(list)
    for i in range(len(giniCluster)):
        giniCellDict[giniCluster[i]].append(count)
        count+=1
    giniCluster=np.array(giniCluster,dtype=int)
    
    count=1
    fanoCellDict = defaultdict(list)
    for i in range(len(fanoCluster)):
        fanoCellDict[fanoCluster[i]].append(count)
        count+=1

    overlapGiniClust=overlapGF(giniCellDict,fanoCellDict,giniCluster)
    minpts=len(overlapGiniClust)/500
    giniClustDict=calMPG(overlapGiniClust,minpts)
    giniIndex=[]
    fanoIndex=[]
    hashUni={}
    for i in range(len(overlapGiniClust)):
        key=str(overlapGiniClust[i])+"_"+str(fanoCluster[i])
        if key not in hashUni.keys():
            giniIndex.append(overlapGiniClust[i])
            fanoIndex.append(fanoCluster[i])
            hashUni[key]=1
    
    giniIndex=np.array(giniIndex)
    fanoIndex=np.array(fanoIndex)
    normGiniIndex=[]
    for i in range(len(giniIndex)):
        normGiniIndex.append(giniClustDict[giniIndex[i]])
    normGiniIndex=np.array(normGiniIndex,dtype='float')
    simMtilde=np.zeros((len(giniIndex),len(fanoIndex)),dtype='float64')
    calMtilde(normGiniIndex,giniIndex,fanoIndex,simMtilde)
    GCconsensus['Mtilde']=simMtilde
    GCconsensus['overlap']=overlapGiniClust
    GCconsensus['giniCellDict']=giniCellDict
    GCconsensus['fanoCellDict']=fanoCellDict
    GCconsensus['giniIndex']=giniIndex
    GCconsensus['fanoIndex']=fanoIndex

def clusterMtilde(GCconsensus):
    K=determinK(GCconsensus['giniCellDict'],GCconsensus['fanoCellDict'])
    kmeans = KMeans(n_clusters=K,n_init=100).fit(GCconsensus['Mtilde'])
    finalClustIndex=kmeans.labels_
    GCconsensus['finalIndex']=np.array(finalClustIndex)

def projectFinalCluster(GCconsensus):
    hashProject={}
    for i in range(len(GCconsensus['finalIndex'])):
        key=str(GCconsensus['giniIndex'][i])+"_"+str(GCconsensus['fanoIndex'][i])
        hashProject[key]=GCconsensus['finalIndex'][i]
    finalClust=[]
    for i in range(len(GCconsensus['overlap'])):
        key=str(GCconsensus['overlap'][i])+"_"+str(GCconsensus['fanoCluster'][i])
        finalClust.append(str(hashProject[key]))
    ######sort and remark clusters######
    remarkClust=[]
    hashFinalCount={}
    for i in range(len(finalClust)):
        hashFinalCount[finalClust[i]]=hashFinalCount.get(finalClust[i],0) + 1
    diCount=[]
    for i in hashFinalCount.keys():
        listCount=[]
        listCount.append(i)
        listCount.append(hashFinalCount[i])
        diCount.append(listCount)
    diCount.sort(key=lambda x:x[1],reverse=True)
    hashFinalProject={}
    for i in range(len(diCount)):
        hashFinalProject[diCount[i][0]]=str(i)
    finalSortedClust=[]
    for i in range(len(finalClust)):
        finalSortedClust.append(hashFinalProject[finalClust[i]])
    GCconsensus['finalCluster']=finalSortedClust
