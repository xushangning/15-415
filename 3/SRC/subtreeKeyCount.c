#include "def.h"

NUMKEYS subtreeKeyCount(PAGENO root) {
    struct PageHdr *left, *right;
    // Follow the leftmost pointer to the leftmost leaf page in the tree.
    PAGENO pgNum = root;
    while (true) {
        left = FetchPage(pgNum);
        if (IsLeaf(left))
            break;
        pgNum = left->KeyListPtr->PgNum;
        FreePage(left);
    }
    // Same for the rightmost leaf.
    for (pgNum = root; ; FreePage(right)) {
        right = FetchPage(pgNum);
        if (IsLeaf(right))
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
