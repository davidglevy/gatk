from __future__ import with_statement
import farm_commands
import os.path
import sys
from optparse import OptionParser
import picard_utils
from gatkConfigParser import *
import re
from itertools import *
import math
import operator

def phredQScore( nMismatches, nBases ):
    #print 'phredQScore', nMismatches, nBases
    if nMismatches == 0:
        return 40
    elif nBases == 0:
        return 0
    else:
        return -10 * math.log10(float(nMismatches) / nBases)
        

def phredScore2ErrorProp(qual):
    #print 'phredScore2ErrorProp', qual
    return math.pow(10.0, float(qual) / -10.0)

def tryByInt(s):
    try:
        return int(s)
    except:
        return s        

expectedHeader = 'rg,dn,Qrep,pos,NBases,MMismatches,Qemp'.split(',')
defaultValues = '0,**,0,0,0,0,0'.split(',')
class RecalData(dict):

    def __init__(self):
        self.parse(expectedHeader, defaultValues)

    def parse(self, header, data):
        # rg,dn,Qrep,pos,NBases,MMismatches,Qemp
        types = [str, str, int, tryByInt, int, int, int]
        for head, expected, datum, type in zip(header, expectedHeader, data, types):
            if head <> expected:
                raise ("Unexpected header in rawData %s %s %s" % (head, expected, datum))
            #print 'Binding => ', head, type(datum)
            self[head] = type(datum)
        #print self
        return self
    
    def set(self, header, values):
        for head, val in zip(header, values):
            self[head] = val
            
    def __getattr__(self, name):
        return self[name]
    
    # rg,dn,Qrep,pos,NBases,MMismatches,Qemp
    def readGroup(self): return self.rg
    def dinuc(self): return self.dn
    def qReported(self): return self.Qrep
    def qEmpirical(self): return self.Qemp
    def cycle(self): return self.pos
    def nBases(self): return self.NBases
    def nMismatches(self): return self.MMismatches
    def nExpectedMismatches(self): return self.nBases() * phredScore2ErrorProp(self.qReported())

    def combine(self, moreData):
        # grab useful info
        sumErrors = self.nExpectedMismatches()
        for datum in moreData:
            self.NBases += datum.nBases()
            self.MMismatches += datum.nMismatches()
            sumErrors += datum.nExpectedMismatches()
        self.updateQemp()
        self.Qrep = phredQScore(sumErrors, self.nBases())
        #print 'self.Qrep is now', self.Qrep
        return self
        
    def updateQemp(self):
        newQemp = phredQScore( self.nMismatches(), self.nBases() )
        #print 'Updating qEmp', self.Qemp, newQemp
        self.Qemp = newQemp
        return newQemp

    def __str__(self):
        return "[rg=%s cycle=%s dinuc=%s qrep=%.1f qemp=%.1f nbases=%d nmismatchs=%d]" % ( self.readGroup(), str(self.cycle()), self.dinuc(), self.qReported(), self.qEmpirical(), self.nBases(), self.nMismatches())
    def __repr__(self):
        return self.__str__()
    
#    def __init__(dinuc, Qrep, pos, nbases, nmismatches, qemp ):
#        self.dinuc = dinuc
#        self.Qrep = Qrep

def rawDataStream(file):
    """Yields successive lists containing the CSVs in the data file; excludes headers"""
    header = None
    for line in open(file):
        if line.find("#") <> -1: continue
        else:
            data = line.strip().split(',')
            if line.find("rg,") <> -1:
                header = data
            else:
                yield RecalData().parse(header, data)

def rawDataByReadGroup(rawDataFile):
    """Yields a stream of the data in rawDataFile, grouped by readGroup"""
    for readGroup, generator in groupby(rawDataStream(rawDataFile), key=RecalData.readGroup):
        yield (readGroup, list(generator))

def combineRecalData(separateData):
    return RecalData().combine(separateData)

def groupRecalData(allData, key=None):
    s = sorted(allData, key=key)
    values = [ [key, combineRecalData(vals)] for key, vals in groupby(s, key=key) ]
    return sorted( values, key=lambda x: x[0])

#
# let's actually analyze the data!
#
def analyzeReadGroup(readGroup, data, outputRoot):
    print 'Read group => ', readGroup
    print 'Number of elements => ', len(data)

    files = []
    if OPTIONS.toStdout:
        basicQualScoreStats(readGroup, data, sys.stdout )
        qReportedVsqEmpirical(readGroup, data, sys.stdout )
        qDiffByCycle(readGroup, data, sys.stdout)
        qDiffByDinuc(readGroup, data, sys.stdout)
    else:
        def outputFile(tail):
            file = outputRoot + tail
            files.append(file)
            return file
            
        with open(outputFile(".basic_info.dat"), 'w') as output:
            basicQualScoreStats(readGroup, data, output )
        with open(outputFile(".empirical_v_reported_quality.dat"), 'w') as output:
            qReportedVsqEmpirical(readGroup, data, output )
        with open(outputFile(".quality_difference_v_cycle.dat"), 'w') as output:
            qDiffByCycle(readGroup, data, output)
        with open(outputFile(".quality_difference_v_dinucleotide.dat"), 'w') as output:
            qDiffByDinuc(readGroup, data, output)
            
    print 'Files', files
    return analyzeFiles(files)

def countQsOfMinQuality(thres, data):
    """Returns RecalData lists for each of the following:
    All quality score bins with qRep > thres, and all quality scores with qRep and qRemp > thres""" 
    qDeclared = RecalData().combine(filter(lambda x: x.qReported() > thres, data))
    qDeclaredTrue = RecalData().combine(filter(lambda x: x.qReported() > thres and x.qEmpirical() > thres, data))
    #print qDeclared
    return qDeclared, qDeclaredTrue

def medianQreported(jaffe, allBases):
    i, ignore = medianByCounts(map( RecalData.nBases, jaffe ))
    return jaffe[i].qReported()

def medianByCounts(counts):
    nTotal = lsum(counts)
    sum = 0.0
    for i in range(len(counts)):
        sum += counts[i]
        if sum / nTotal > 0.5:  
            # The current datum contains the median
            return i, counts[i]

def modeQreported(jaffe, allBases):
    ordered = sorted(jaffe, key=RecalData.nBases, reverse=True )
    #print ordered
    return ordered[0].qReported()

def averageQreported(jaffe, allBases):
    # the average reported quality score is already calculated and stored as qRep!
    return allBases.qReported()

def lsum(inlist):
    return reduce(operator.__add__, inlist, 0)

def lsamplestdev (inlist, counts, mean):
    """
    Returns the variance of the values in the passed list using
    N for the denominator (i.e., DESCRIBES the sample variance only).

    Usage:   lsamplevar(inlist)"""
    n = lsum(counts)
    sum = 0.0
    for item, count in zip(inlist, counts):
        diff = item - mean
        inc = count * diff * diff
        #print item, count, mean, diff, diff*diff, inc
        sum += inc
    return math.sqrt(sum / float(n-1))

def rmse(reportedList, empiricalList, counts):
    sum = 0.0
    for reported, empirical, count in zip(reportedList, empiricalList, counts):
        diff = reported - empirical
        inc = count * diff * diff
        sum += inc
    return math.sqrt(sum)

def stdevQReported(jaffe, allBases):
    mean = averageQreported(jaffe, allBases)
    return lsamplestdev(map( RecalData.qReported, jaffe ), map( RecalData.nBases, jaffe ), mean)

def coeffOfVariationQreported(jaffe, allBases):
    mean = averageQreported(jaffe, allBases)
    stdev = stdevQReported(jaffe, allBases)
    return stdev / mean

#    o("variance_Qreported                           %2.2f" % varianceQreported(jaffe))

def rmseJaffe(jaffe):
    return rmse( map( RecalData.qReported, jaffe ), map( RecalData.qEmpirical, jaffe ), map( RecalData.nBases, jaffe ) )

def basicQualScoreStats(readGroup, data, output ):
    def o(s):
        print >> output, s
    # aggregate all the data into a single datum
    rg, allBases = groupRecalData(data, key=RecalData.readGroup)[0]
    #o(allBases)
    o("read_group                                   %s" % rg)
    #o("number_of_cycles %d" % 0)
    #o("maximum_reported_quality_score %d" % 0)
    o("number_of_bases                              %d" % allBases.nBases())
    o("number_of_mismatching_bases                  %d" % allBases.nMismatches())
    o("lane_wide_Qreported                          %2.2f" % allBases.qReported())
    o("lane_wide_Qempirical                         %2.2f" % allBases.qEmpirical())
    o("lane_wide_Qempirical_minus_Qreported         %2.2f" % (allBases.qEmpirical()-allBases.qReported()))

    jaffe = [datum for key, datum in qReportedVsqEmpiricalStream(readGroup, data)]

    o("median_Qreported                             %2.2f" % medianQreported(jaffe, allBases))
    o("mode_Qreported                               %2.2f" % modeQreported(jaffe, allBases))
    o("average_Qreported                            %2.2f" % averageQreported(jaffe, allBases))
    o("stdev_Qreported                              %2.2f" % stdevQReported(jaffe, allBases))
    o("coeff_of_variation_Qreported                 %2.2f" % coeffOfVariationQreported(jaffe, allBases))

    o("RMSE(qReported,qEmpirical)                   %2.2f" % rmseJaffe(jaffe))
    for thres in [20, 25, 30]:
        qDeclared, qDeclaredTrue = countQsOfMinQuality(thres, jaffe)
        o("number_of_q%d_bases                          %d" % (thres, qDeclared.nBases()))
        o("percent_of_q%d_bases                         %2.2f" % (thres, 100 * qDeclared.nBases() / float(allBases.nBases())))
        o("number_of_q%d_bases_with_qemp_above_q%d      %d" % (thres, thres, qDeclaredTrue.nBases()))
        o("percent_of_q%d_bases_with_qemp_above_q%d     %2.2f" % (thres, thres, 100 * qDeclaredTrue.nBases() / float(allBases.nBases())))

def qDiffByCycle(readGroup, allData, output):
    print >> output, '# Note Qreported is a float here due to combining Qreported across quality bins -- Qreported is the expected Q across all Q bins, weighted by nBases'
    print >> output, 'Cycle    Qreported   Qempirical     Qempirical_Qreported     nMismatches     nBases'
    for cycle, datum in groupRecalData(allData, key=RecalData.cycle):
        datum.set(['rg', 'dn', 'pos'], [readGroup, '**', cycle])
        diff = datum.qEmpirical() - datum.qReported()
        print >> output, "%s   %2.2f  %2.2f   %2.2f     %12d    %12d" % (datum.cycle(), datum.qReported(), datum.qEmpirical(), diff, datum.nMismatches(), datum.nBases())

def qDiffByDinuc(readGroup, allData, output):
    print >> output, '# Note Qreported is a float here due to combining Qreported across quality bins -- Qreported is the expected Q across all Q bins, weighted by nBases'
    print >> output, 'Dinuc    Qreported   Qempirical     Qempirical_Qreported     nMismatches     nBases'
    for dinuc, datum in groupRecalData(allData, key=RecalData.dinuc):
        datum.set(['rg', 'dn', 'pos'], [readGroup, dinuc, '*'])
        diff = datum.qEmpirical() - datum.qReported()
        print >> output, "%s   %2.2f  %2.2f   %2.2f     %12d    %12d" % (datum.dinuc(), datum.qReported(), datum.qEmpirical(), diff, datum.nMismatches(), datum.nBases())

def qReportedVsqEmpiricalStream(readGroup, data):
    for key, datum in groupRecalData(data, key=RecalData.qReported):
        datum.set(['rg', 'dn', 'Qrep', 'pos'], [readGroup, '**', key, '*'])
        yield key, datum

def qReportedVsqEmpirical(readGroup, allData, output):
    print >> output, 'Qreported    Qempirical   nMismatches     nBases'
    for key, datum in qReportedVsqEmpiricalStream(readGroup, allData):
        print >> output, "%2.2f  %2.2f   %12d    %12d" % (datum.qReported(), datum.qEmpirical(), datum.nMismatches(), datum.nBases())

def analyzeRawData(rawDataFile):
    for readGroup, data in rawDataByReadGroup(rawDataFile):
        if OPTIONS.selectedReadGroups == [] or readGroup in OPTIONS.selectedReadGroups:
            root, sourceFilename = os.path.split(rawDataFile)
            if ( OPTIONS.outputDir ): root = OPTIONS.outputDir
            outputRoot = os.path.join(root, "%s.%s.%s" % ( sourceFilename, readGroup, 'analysis' ))
            analyzeReadGroup(readGroup, data, outputRoot)

plottersByFile = {
    "raw_data.csv$" : analyzeRawData,
    "recal_data.csv$" : analyzeRawData,
    "empirical_v_reported_quality" : 'PlotQEmpStated',
    "quality_difference_v_dinucleotide" : 'PlotQDiffByDinuc',
    "quality_difference_v_cycle" : 'PlotQDiffByCycle' }

def getPlotterForFile(file):
    for pat, analysis in plottersByFile.iteritems():
        if re.search(pat, file):
            if type(analysis) == str:
                return config.getOption('R', analysis, 'input_file')
            else:
                analysis(file)
    return None

def analyzeFiles(files):
    #print 'analyzeFiles', files
    Rscript = config.getOption('R', 'Rscript', 'input_file')
    for file in files:
        plotter = getPlotterForFile(file)
        if plotter <> None:
            cmd = ' '.join([Rscript, plotter, file])
            farm_commands.cmd(cmd, None, None, just_print_commands = OPTIONS.dry)

def main():
    global config, OPTIONS
    usage = """usage: %prog -c config.cfg files*"""

    parser = OptionParser(usage=usage)
    parser.add_option("-q", "--farm", dest="farmQueue",
                        type="string", default=None,
                        help="Farm queue to send processing jobs to")
    parser.add_option("-d", "--dir", dest="outputDir",
                        type="string", default=None,
                        help="If provided, analysis output files will be written to this directory")
    parser.add_option("-c", "--config", dest="configs",
                        action="append", type="string", default=[],
                        help="Configuration file")                        
    parser.add_option("-s", "--stdout", dest="toStdout",
                        action='store_true', default=False,
                        help="If provided, writes output to standard output, not to files")
    parser.add_option("", "--dry", dest="dry",
                        action='store_true', default=False,
                        help="If provided, nothing actually gets run, just a dry run")
    parser.add_option("-g", "--readGroup", dest="selectedReadGroups",
                        action="append", type="string", default=[],
                        help="If provided, only the provided read groups will be analyzed")                        
                        
    (OPTIONS, args) = parser.parse_args()
    #if len(args) != 3:
    #    parser.error("incorrect number of arguments")

    if len(OPTIONS.configs) == 0:
        parser.error("Requires at least one configuration file be provided")

    config = gatkConfigParser(OPTIONS.configs)
  
    analyzeFiles(args)

import unittest
class TestanalzyeRecalQuals(unittest.TestCase):
    def setUp(self):
        self.numbers = [0, 1, 2, 2, 3, 4, 4, 4, 5, 5, 5, 6, 6]
        self.numbersItems  = [0, 1, 2, 3, 4, 5, 6]
        self.numbersCounts = [1, 1, 2, 1, 3, 3, 2]
        self.numbers_sum = 47
        self.numbers_mean = 3.615385
        self.numbers_mode = 4
        self.numbers_median = 4
        self.numbers_stdev = 1.894662
        self.numbers_var = 3.589744
        self.numbers_cov = self.numbers_stdev / self.numbers_mean
        
    def testSum(self):
        self.assertEquals(self.numbers_sum, lsum(self.numbers))
        self.assertEquals(0, lsum(self.numbers[0:0]))
        self.assertEquals(1, lsum(self.numbers[0:2]))
        self.assertEquals(3, lsum(self.numbers[0:3]))

    def teststdev(self):
        self.assertAlmostEqual(self.numbers_stdev, lsamplestdev(self.numbersItems, self.numbersCounts, self.numbers_mean), 4)

if __name__ == '__main__':
    main()    
    #unittest.main()    
    