#include "def.h"

NUMKEYS subtreeKeyCount(PAGENO pgNum) {
    struct PageHdr *left, *right;
    PAGENO root = pgNum;
    // Follow the leftmost pointer to the leftmost leaf page in the tree.
    while (true) {
        left = FetchPage(pgNum);
        if (left->PgTypeID == 'L')
            break;
        pgNum = left->KeyListPtr->PgNum;
        FreePage(left);
    }
    // Same for the rightmost leaf.
    for (pgNum = root; ; FreePage(right)) {
        right = FetchPage(pgNum);
        if (right->PgTypeID == 'L')
            break;
        pgNum = right->PtrToFinalRtgPg;
    }

    // Count the keys.
    NUMKEYS count = 0;
    while (true) {
        count += left->NumKeys;
        if (left->PgNum == right->PgNum)
            break;
        pgNum = left->PgNumOfNxtLfPg;
        FreePage(left);
        left = FetchPage(pgNum);
    }
    FreePage(left);
    FreePage(right);

    return count;
}
