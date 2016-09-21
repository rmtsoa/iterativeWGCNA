# pylint: disable=invalid-name
# pylint: disable=no-self-use
# pylint: disable=too-many-instance-attributes
# pylint: disable=redefined-variable-type

'''
manage network (for summaries)
'''

from __future__ import print_function
from __future__ import with_statement

import logging

from random import randint
from collections import OrderedDict

import rpy2.robjects as ro

from .wgcna import WgcnaManager
from .r.imports import grdevices, base, rsnippets

from .eigengenes import Eigengenes

class Network(object):
    '''
    a network contains the classified genes
    and their assignments
    hash of modules and properties
    for summary purposes
    '''

    def __init__(self, args):
        self.logger = logging.getLogger('iterativeWGCNA.Network')
        self.args = args
        self.eigengenes = None

        self.genes = None
        self.modules = None
        self.classifiedGenes = None
        self.profiles = None
        self.kme = None
        self.membership = None

        # self.graph = None
        self.geneColors = None
        self.adjacency = None
        self.weightedAdjacency = None # weighted by shared membership


    def build(self, genes, eigengenes):
        '''
        build from iterativeWGCNA result in memory
        '''
        self.eigengenes = eigengenes
        self.genes = genes.get_genes()
        self.classifiedGenes = genes.get_classified_genes()
        self.profiles = genes.profiles
        self.kme = genes.get_gene_kME()
        self.membership = genes.get_gene_membership()

        self.modules = OrderedDict((module, {'color':None, 'kIn':0, 'kOut':0}) \
                                       for module in genes.get_modules())
        self.modules.update({'UNCLASSIFIED': {'color':None, 'kIn':'NA', 'kOut':'NA'}})

        self.__assign_colors()
        self.__generate_weighted_adjacency()


    def __assign_colors(self):
        self.__generate_module_colors()
        self.geneColors = OrderedDict((gene, None) for gene in self.genes)
        self.assign_gene_colors()


    def build_from_file(self, profiles):
        '''
        initialize Network from iterativeWGCNA output found in path
        '''
        self.profiles = profiles
        self.genes = self.profiles.genes()

        # when membership is loaded from file, modules and classified
        # genes are determined as well
        self.classifiedGenes = []
        self.modules = []
        self.membership = self.__load_membership_from_file()
        self.modules = OrderedDict((module, {'color':None, 'kIn':0, 'kOut':0}) \
                                       for module in self.modules)
        self.modules['UNCLASSIFIED']['color'] = None
        self.modules['UNCLASSIFIED']['kIn'] = 'NA'
        self.modules['UNCLASSIFIED']['kOut'] = 'NA'

        self.logger.debug(self.modules)

        self.kme = self.__load_kme_from_file()

        self.eigengenes = Eigengenes()
        self.eigengenes.load_matrix_from_file("eigengenes.txt")

        # TODO fix error: 
        # self.geneColors[g] = self.modules[self.membership[g]]['color']
        # TypeError: 'NoneType' object has no attribute '__getitem_'_
        
        # self.__assign_colors()
        # self.__generate_weighted_adjacency()


    def __load_membership_from_file(self):
        '''
        loads membership assignments from file
        and assembles list of classified genes
        and determines list of unique modules
        '''
        membership = ro.DataFrame.from_csvfile("membership.txt", sep='\t',
                                               header=True, row_names=1, as_is=True)

        finalIndex = membership.names.index('final')
        self.membership = OrderedDict((gene, None) for gene in self.genes)
        for g in self.genes:
            module = membership.rx(g, finalIndex)[0]
            self.modules.append(module)
            self.membership[g] = module
            if module != 'UNCLASSIFIED':
                if 'p' not in module:
                    self.logger.debug("Module: " + module + "; Gene: " + g)
                self.classifiedGenes.append(g)
        # self.logger.debug(self.modules)
        self.modules = list(set(self.modules)) # gets unique list of modules


    def __load_kme_from_file(self):
        '''
        loads kME to assigned module from file
        '''
        kME = ro.DataFrame.from_csvfile("eigengene-connectivity.txt", sep='\t',
                                        header=True, row_names=1, as_is=True)

        finalIndex = kME.names.index('final')
        self.kme = OrderedDict((gene, None) for gene in self.genes)
        for g in self.genes:
            self.kme[g] = kME.rx(g, finalIndex)[0]


    def summarize_network(self):
        '''
        generate summary figs and data
        '''

        self.plot_eigengene_network()
        if self.args.generateNetworkSummary is not None:
            self.__plot_summary_views()

        if self.args.summarizeModules:
            self.__summarize_network_modularity()
            self.logger.debug(self.modules)
            self.__write_module_summary()
            # self summarize modules --> heatmaps, kme


    def __generate_random_color(self, colors):
        '''
        generate a random color
        '''
        # TODO probably a better way to do this, but...
        # since we may need > 50 colors, random it is
        color = '#' + '%06X' % randint(0, 0xFFFFFF)
        while color in colors:
            color = '#' + '%06X' % randint(0, 0xFFFFFF)
        return color


    def __generate_module_colors(self):
        '''
        generate module color map
        '''
        colors = []
        for m in self.modules:
            color = self.__generate_random_color(colors)
            colors.append(color)
            self.modules[m]['color'] = color

        self.modules["UNCLASSIFIED"]['color'] = '#D3D3D3'


    def assign_gene_colors(self):
        '''
        assign colors to genes according to module membership
        '''
        for g in self.genes:
            self.geneColors[g] = self.modules[self.membership[g]]['color']


    def get_gene_colors(self, targetGenes):
        '''
        retrieve colors for specified gene list
        '''
        colors = [color for gene, color in self.geneColors.items() if gene in targetGenes]
        return colors


    def plot_eigengene_network(self):
        '''
        wrapper for plotting the eigengene network to pdf
        '''
        grdevices().pdf("eigengene-network.pdf")
        manager = WgcnaManager(self.eigengenes.matrix, self.args.wgcnaParameters)
        manager.plot_eigengene_network()
        grdevices().dev_off()


    def plot_network_summary(self, genes, title, filename):
        '''
        wrapper for WGCNA summary network view (heatmap + dendrogram)
        '''

        expression = self.profiles.gene_expression(genes)
        colors = self.get_gene_colors(genes)
        manager = WgcnaManager(expression, self.args.wgcnaParameters)
        grdevices().pdf(filename)
        manager.plot_network_overview(colors, title)
        grdevices().dev_off()


    def __plot_summary_views(self):
        '''
        plot summary heatmaps/views
        '''
        if self.args.generateNetworkSummary == 'input' \
           or self.args.generateNetworkSummary == 'all':
            self.plot_network_summary(self.genes,
                                      "All Genes (incl. unclassified)",
                                      "input-block-diagram.pdf")

        if self.args.generateNetworkSummary == 'network' \
           or self.args.generateNetworkSummary == 'all':
            self.plot_network_summary(self.classifiedGenes,
                                      "Network (classified genes)",
                                      "network-block-diagram.pdf")


    def __get_module_members(self, targetModule):
        '''
        get genes in targetModule
        '''
        return [gene for gene, module in self.membership.items() if module == targetModule]


    def __generate_weighted_adjacency(self):
        '''
        gene x gene weight matrix with matrix[r][c] = 1
        if genes r & c are in the same module; for
        weighted graph viz and to simply
        calc of in/out degree
        '''

        manager = WgcnaManager(self.profiles.gene_expression(self.classifiedGenes),
                               self.args)
        manager.adjacency(True, True, True) # signed, but filter negatives & self-refs
        self.adjacency = base().as_data_frame(manager.adjacencyMatrix)
        self.weightedAdjacency = self.adjacency

        for m in self.modules:
            if m == 'UNCLASSIFIED':
                continue

            members = self.__get_module_members(m)
            for r in members:
                indexR = self.weightedAdjacency.names.index(r)
                for c in members:
                    if r == c:
                        continue
                    indexC = self.weightedAdjacency.names.index(c)
                    adj = self.adjacency[indexR][indexC]
                    if adj > 0:
                        self.weightedAdjacency[indexR][indexC] = adj + 1


    def calculate_degree_modularity(self, targetModule):
        '''
        calculates in degree (kIn) and out degree (kOut)
        for the target module
        '''
        members = self.__get_module_members(targetModule)
        # self.logger.debug(targetModule)
        # self.logger.debug(members)
        degree = rsnippets.degree(self.adjacency, ro.StrVector(members),
                                  self.args.edgeWeight)
        self.modules[targetModule]['kIn'] = int(degree.rx2('kIn')[0])
        self.modules[targetModule]['kOut'] = int(degree.rx2('kOut')[0])


    def __summarize_network_modularity(self):
        '''
        summarize modularity of network
        calculates in degree (kIn) and out degree (kOut) per module
        '''
        for m in self.modules:
            if m != 'UNCLASSIFIED':
                self.calculate_degree_modularity(m)


    def __get_module_size(self, targetModule):
        '''
        return # of module members for target module
        '''
        return len(self.__get_module_members(targetModule))


    def __write_module_summary(self):
        '''
        writes network modularity to a file
        '''
        fileName = 'module-summary.txt'
        with open(fileName, 'w') as f:
            header = ('Module', 'Size', 'Color', 'kIn', 'kOut')
            print('\t'.join(header), file=f)
            for m in self.modules:
                print(m,
                      self.__get_module_size(m),
                      self.modules[m]['color'],
                      self.modules[m]['kIn'],
                      self.modules[m]['kOut'], sep='\t', file=f)


    def export_cytoscape_json(self):
        '''
        creates and saves a cytoscape json file
        '''
        
        filterLevel = self.args.edgeWeight

        if self.weightedAdjacency is None:
            self.__generate_weighted_adjacency()

        
