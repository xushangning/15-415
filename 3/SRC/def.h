/*****************************************************************************
*                                                                            *
*    This is the definition file for the B-Tree program.  It contains        *
*    declarations for all functions utilized; program macros and             *
*    constants; a few necessary globals; typedef declarations; and           *
*    structure definitions.                                                  *
*                                                                            *
*    Consult the Programmer's Manual ("Pgmrs.Man") for the program           *
*    description.                                                            *
*                                                                            *
*****************************************************************************/

#include <stdio.h>
#include "defn.g"
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdbool.h>

extern int PAGESIZE;	/* Size of page (in bytes) to be stored on disk  */
extern int MAXTEXTPTRS;	/* POSTINGSFILE stores so many ptrs,
			   then goes to overflow */

#define MAXWORDSIZE (100) /* Maximum size of any key */
#define ROOT (1)          /* The root is always stored as first page on disk */
#define FIRSTLEAFPG (2)   /* The page number of first (orginal) leaf page */
#define LeafSymbol ('L')     /* To differentiate a Leaf page */  
#define NonLeafSymbol ('N')  /* To differentiate a Nonleaf page */
#define IsLeaf(x)     (LeafSymbol == (x)->PgTypeID)
#define IsNonLeaf(x)  (NonLeafSymbol == (x)->PgTypeID)
#define TRUE		(1)
#define FALSE		(0)
#define EOH		(-1)	/* end of the hash table */
#define NULLPAGENO	(-3)	/* null page pointer */
#define NONEXISTENT	(-2)

typedef long PAGENO;
typedef long TEXTPTR;
typedef long POSTINGSPTR;
typedef int  KEYLEN;
typedef int  NUMKEYS;
typedef int  NUMBYTES; 
typedef long  NUMPTRS;     /* needed to make contiguous postings easier */

#define gotoeof(x)	fseek((x), (long) 0, 2);

/**
 * The following structure is utilized for holding a page of the B-Tree.  It is
 * used for both Leaf and NonLeaf pages.  The pages are differentiated by the
 * first byte which contains 'L' if it is a Leaf page or 'N' if it is a NonLeaf
 * page.  All Leaf pages contain the field 'PgNumOfNxtLfPg' which is a pointer
 * (page number) to the next logical leaf page.  All NonLeaf pages contain the
 * field 'PtrToFinalRtgPg' which is a pointer (page number) to the rightmost
 * child.
 */
struct PageHdr {
    /**
     * 'N' for NonLeaf, 'L' for Leaf
     */
    char              PgTypeID;

    /**
     * Page number within the B-Tree
     */
    PAGENO           PgNum;

    /**
     * Page number of next logical leaf page (LEAF PAGES ONLY)
     */
    PAGENO           PgNumOfNxtLfPg;

    /**
     * Number of bytes stored within page
     */
    NUMBYTES          NumBytes;

    /**
     * Number of keys stored within page
     */
    NUMKEYS           NumKeys;

    NUMKEYS            SubtreeKeyCount; /* THIS IS YOUR TASK :) */

    /**
     * Pointer to the list of keys and their relative data
     */
    struct KeyRecord *KeyListPtr;

    /**
     * Page number of rightmost child (NONLEAF PAGES ONLY)
     */
    PAGENO           PtrToFinalRtgPg;
};


/**
 * The following structure is used to hold the keys which are stored in the
 * B-Tree page.  It is used for both Leaf and NonLeaf keys. If the page is a
 * NonLeaf page, the key will be accompanied by the field 'PgNum' which is a
 * pointer (page number) to a left child page that contains keys which are
 * lexicographically less than the the key in this page.  If the page is a Leaf
 * page, the key will be accompanied by the field 'Posting' which is a pointer
 * (offset) into the POSTINGSFILE (which contains the offsets into the Text
 * file).
 */
struct KeyRecord {
    /**
     * Page number of child page containing keys lexicographically less than
     * or equal to `StoredKey` (NONLEAF PAGES ONLY).
     *
     * @details
     * The claim in the
     * [slide](https://15415.courses.cs.cmu.edu/fall2016/hws/HW3/BtreeStruct.pdf)
     * that when `KeyRecord` is a not a leaf, `PgNum`'s corresponding page
     * contains keys less than `StoredKey` is wrong. It actually contains keys
     * less than or equal to `StoredKey`. Check
     * SplitPage(struct PageHdr *PagePtr) for yourself.
     */
     PAGENO           PgNum;

     /**
      * The length (in bytes) of the stored key
      */
     KEYLEN            KeyLen;

     /**
      * A pointer to the dynamically allocated storage for the key containing
      * up to MAXWORDSIZE characters
      */
     char             *StoredKey;

     /**
      * Offset of Postings record (LEAF PAGES ONLY)
      */
     POSTINGSPTR       Posting;

     /**
      * Pointer to the next logical KeyRecord structure
      */
     struct KeyRecord *Next;
};

/**
 * Holds the key to be moved upwards upon splitting.
 */
struct upKey {
	PAGENO		left;	/* left page, with keys <= */
	PAGENO		right;	/* right page, with keys > */
	char *		key;
};

struct PageHdr *FetchPage(PAGENO Page);
struct upKey *SplitPage(struct PageHdr * PagePtr);
void FreePage(struct PageHdr *PagePtr);
void FlushPage(struct PageHdr *PagePtr);

int FindInsertionPosition(struct KeyRecord * KeyListTraverser, char *Key,
                          bool *Found, NUMKEYS NumKeys, int Count);
struct upKey *InsertKeyInLeaf(struct PageHdr * PagePtr, char *Key,
                              TEXTPTR TextOffset, bool *duplicate_key);
struct upKey *InsertKeyInNonLeaf(struct PageHdr * PagePtr, struct upKey * MiddleKey);
struct upKey *PropagatedInsertion(PAGENO PageNo, char *Key, TEXTPTR TextOffset, bool *duplicate_key);

void PrintTreeInOrder(PAGENO pgNum, int level);
NUMKEYS subtreeKeyCount(PAGENO root);
