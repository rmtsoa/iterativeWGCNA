#!/usr/bin/env python2.7
"""
uses rpy2 python library to create a namespace for R functions underlying iterativeWGCNA
"""

FUNCTIONS = """

# convert numeric data frame to real
numeric2real <- function(df) {
     df * 1.0
}

# return 1-matrix
dissMatrix <- function(df) {
    1.0 - df
}

# add a constant value
add <- function(df, value) {
    df + value
}

# return power-weighted matrix
powerWeightMatrix <- function(df, power) {
    df^power
}


# set values < thresshold to 0
filterByThreshold <- function(df, threshold) {
    df[df < threshold] <- 0
    df
}


# set value of matrix diagonal
diag <- function(df, value) {
    diag(df) <- value
    df
}

# wrapper for save object b/c doesn't seem to work with rpy2
saveObject <- function(obj, objName, file) {
   assign(objName, obj)
   save(list=c(objName), file = file)
}

# calculate degree summary for module genes
degree <- function(adjMatrix, members, threshold) {
    adjSubset <- adjMatrix[members, members]
    inDegree = sum(adjSubset >= threshold) / 2
    adjSubset <- adjMatrix[members,  !names(adjMatrix) %in% members]
    outDegree <- sum(adjSubset >= threshold)
    list(kIn=inDegree, kOut=outDegree)
}


# given WGCNA blocks, extracts and transposes eigengene matrix
# labels columns (samples)
# cleans up module names (removes the "ME")

extractEigengenes <- function(iteration, blocks, sampleNames) {
    eigengenes <- as.data.frame(t(blocks$MEs))
    colnames(eigengenes) <- sampleNames
    eigengenes <- eigengenes[row.names(eigengenes) != "ME0" & row.names(eigengenes) != "MEgrey", ]
    row.names(eigengenes) <- gsub("ME", paste(iteration, "-", sep=""), row.names(eigengenes))
    eigengenes
}

# given WGCNA blocks and gene names, returns
# a data frame with modules mapped to gene names
extractModules <- function(blocks, geneNames) {
    as.data.frame(blocks$colors, row.names = geneNames)
}

# extract module members
# does not assume same ordering
extractMembers <- function(module, expr, membership) {
    membership <- unlist(membership)
    membership <- membership[row.names(expr)]
    members <- membership == module
    expr[members, ]
}

# remove unclassified from expression set
removeUnclassified <- function(expr, membership) {
    membership <- unlist(membership)
    membership <- membership[row.names(expr)]
    classified = membership != "UNCLASSIFIED"
    expr[classified, ]
}

# blue, white, red color scale
BlWhRed <- function() {
    colorRampPalette(c("blue", "white", "red"))(100)
}

# white, yellow, red color scale
WhYlRed <- function() {
   colorRampPalette(c("white", "yellow", "red"))(100)
}

# create color scale by passing a string vector of colors
colorScale <- function(colors) {
   colorRampPalette(colors)(100)
}

"""

__author__ = "Emily Greenfest-Allen"
__copyright__ = "Copyright 2016, University of Pennsylvania"
