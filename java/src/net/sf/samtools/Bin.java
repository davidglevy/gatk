package net.sf.samtools;

import java.util.List;

/**
 * An individual bin in a BAM file, divided into chunks plus a linear index. 
 *
 * @author mhanna
 * @version 0.1
 */
public class Bin implements Comparable {
    /**
     * The reference sequence associated with this bin.
     */
    public final int referenceSequence;

    /**
     * The number of this bin within the BAM file.
     */
    public final int binNumber;

    /**
     * The chunks contained within this bin.
     */
    public final List<Chunk> chunks;

    public Bin(int referenceSequence, int binNumber, List<Chunk> chunks) {
        this.referenceSequence = referenceSequence;
        this.binNumber = binNumber;
        this.chunks = chunks;
    }

    /**
     * See whether two bins are equal.  If the ref seq and the bin number
     * are equal, assume equality of the chunk list.
     * @param other The other Bin to which to compare this.
     * @return True if the two bins are equal.  False otherwise.
     */
    public boolean equals(Object other) {
        if(other == null) return false;
        if(!(other instanceof Bin)) return false;

        Bin otherBin = (Bin)other;
        return this.referenceSequence == otherBin.referenceSequence && this.binNumber == otherBin.binNumber;
    }

    /**
     * Compare two bins to see what ordering they should appear in.
     * @param other Other bin to which this bin should be compared.
     * @return -1 if this < other, 0 if this == other, 1 if this > other.
     */
    public int compareTo(Object other) {
        if(other == null)
            throw new ClassCastException("Cannot compare to a null object");
        Bin otherBin = (Bin)other;

        // Check the reference sequences first.
        if(this.referenceSequence != otherBin.referenceSequence)
            return ((Integer)referenceSequence).compareTo(otherBin.referenceSequence);

        // Then check the bin ordering.
        return ((Integer)binNumber).compareTo(otherBin.binNumber);
    }
}
