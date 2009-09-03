package org.broadinstitute.sting.playground.utils;

import net.sf.samtools.SAMRecord;

import java.util.List;
import java.util.ArrayList;

import org.broadinstitute.sting.utils.Pair;

/**
 * Created by IntelliJ IDEA.
 * User: chartl
 * Date: Aug 27, 2009
 * Time: 12:31:08 PM
 * To change this template use File | Settings | File Templates.
 */
public class PoolUtils {

    private PoolUtils () {}

    public static final int BASE_A_OFFSET = 0;
    public static final int BASE_C_OFFSET = 1;
    public static final int BASE_G_OFFSET = 2;
    public static final int BASE_T_OFFSET = 3;
    public static final int BASE_INDEXED_ARRAY_SIZE = 4;

    public static Pair<Pair<List<SAMRecord>, List<SAMRecord>>,Pair<List<Integer>,List<Integer>>> splitReadsByReadDirection(List<SAMRecord> reads, List<Integer> offsets) {
        ArrayList<SAMRecord> forwardReads;
        ArrayList<SAMRecord> reverseReads;
        ArrayList<Integer> forwardOffsets;
        ArrayList<Integer> reverseOffsets;

        if ( reads == null) {
            forwardReads = null;
            reverseReads = null;
            forwardOffsets = null;
            reverseOffsets = null;
        } else {
            forwardReads = new ArrayList();
            reverseReads = new ArrayList();
            forwardOffsets = new ArrayList();
            reverseOffsets = new ArrayList();

            for ( int readNo = 0; readNo < reads.size(); readNo ++ ) {
                if ( reads.get(readNo).getReadNegativeStrandFlag() ) {
                    forwardReads.add(reads.get(readNo));
                    forwardOffsets.add(offsets.get(readNo));
                } else {
                    reverseReads.add(reads.get(readNo));
                    reverseOffsets.add(offsets.get(readNo));
                }
            }
        }

        return new Pair(new Pair(forwardReads,reverseReads), new Pair(forwardOffsets,reverseOffsets));
    }

    public static Pair<List<SAMRecord>[], List<Integer>[]> splitReadsByBase(List<SAMRecord> reads, List<Integer> offsets) {
        ArrayList<SAMRecord>[] readsByBase;
        ArrayList<Integer>[] offsetsByBase;
        if ( reads == null ) {
            readsByBase = null;
            offsetsByBase = null;
        }  else {
            readsByBase = new ArrayList[4];
            offsetsByBase = new ArrayList[4];
            for(int readNum = 0; readNum < reads.size(); readNum++) {
                switch (reads.get(readNum).getReadBases()[offsets.get(readNum)]) {
                    case 'A':
                    case 'a': readsByBase[0].add(reads.get(readNum));
                        offsetsByBase[0].add(offsets.get(readNum));
                        break;
                    case 'C':
                    case 'c': readsByBase[1].add(reads.get(readNum));
                        offsetsByBase[1].add(offsets.get(readNum));
                        break;
                    case 'G':
                    case 'g': readsByBase[2].add(reads.get(readNum));
                        offsetsByBase[2].add(offsets.get(readNum));
                        break;
                    case 'T':
                    case 't': readsByBase[3].add(reads.get(readNum));
                        offsetsByBase[3].add(offsets.get(readNum));
                        break;
                    default: break; // TODO: INDEL AWARENESS
                }
            }
        }
        return new Pair(readsByBase,offsetsByBase);
    }

    public static Pair<List<SAMRecord>, List<Integer>> thresholdReadsByQuality(List<SAMRecord> reads, List<Integer> offsets, byte qThresh) {
        List<SAMRecord> threshReads;
        List<Integer> threshOffsets;
        if(reads == null) {
            threshReads=null;
            threshOffsets = null;
        } else if (qThresh <= 0) {
            threshReads = reads;
            threshOffsets = offsets;
        } else {
            threshReads = new ArrayList();
            threshOffsets = new ArrayList();

            for ( int readNo = 0; readNo < reads.size(); readNo ++) {
                if ( reads.get(readNo).getBaseQualities()[offsets.get(readNo)] >= qThresh) {
                    threshReads.add(reads.get(readNo));
                    threshOffsets.add(offsets.get(readNo));
                } // else do nothing
            }
        }

        return new Pair(threshReads,threshOffsets);
    }

    public static int getBaseOffset(char base) {
        switch(base) {
            case 'A':
            case 'a':
                return getBaseAOffset();
            case 'C':
            case 'c':
                return getBaseCOffset();
            case 'G':
            case 'g':
                return getBaseGOffset();
            case 'T':
            case 't':
                return getBaseTOffset();
            default:
                return -1;
        }
        //TODO: indel offsets
        }

    public static int getBaseAOffset() {
        return BASE_A_OFFSET;
    }

    public static int getBaseCOffset() {
        return BASE_C_OFFSET;
    }

    public static int getBaseGOffset() {
        return BASE_G_OFFSET;
    }

    public static int getBaseTOffset() {
        return BASE_T_OFFSET;
    }

    public static List<Byte> getListOfBaseQualities(List<SAMRecord> reads,List<Integer> offsets) {
        //TODO: this is a terrible method name. Change it to something better.
        List<Byte> qualities = new ArrayList<Byte>(reads.size());
        for (int readNo = 0; readNo < reads.size(); readNo ++) {
            qualities.add(reads.get(readNo).getBaseQualities()[offsets.get(readNo)]);
        }

        return qualities;
    }
}
