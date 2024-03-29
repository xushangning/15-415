
/***************************************************************************
*                                                                          *
*    This function splits leaf and nonleaf pages.  The page is split       *
*    according to the number of keys it contains.  Half remain in the      *
*    current page (half + one in the case where the total number of        *
*    keys is an odd number), and half are transferred to a newly created   *
*    page.  The two pages are written to disk (FlushPage()).  The          *
*    function returns the middle key which is to be inserted in the        *
*    parent page,                                                          *
     in an "upKey" structure

*                                                                          *
***************************************************************************/

#include "def.h"

struct upKey *SplitPage(struct PageHdr *PagePtr) {
    int i;
    NUMKEYS FirstHalfNumKeys;
    struct PageHdr *newPagePtr; /* to hold the new page image */
    PAGENO getNewPageNum(void);
    char *strsave(char *s);

    struct KeyRecord *pbefore, /* points to the record before the middle */
        *pmiddle,              /* points to the middle-th record, */
        /* which will be pushed upstairs */
        *pafter; /* points to the successor of *pmiddle */

    struct upKey *upk; /* structure with middle key, */
                       /* to be returned upwards */

    /* Determine the number of keys to remain in current page and
       the number to be transferred to new page                */
    if (PagePtr->NumKeys % 2 == 0)
        FirstHalfNumKeys = PagePtr->NumKeys / 2;
    else
        FirstHalfNumKeys = (PagePtr->NumKeys / 2) + 1;

    /* Traverse list of keys up to the key before the middle */
    pbefore = PagePtr->KeyListPtr;
    for (i = 1; i < (FirstHalfNumKeys - 1); i++) {
        pbefore = pbefore->Next;
    }
    pmiddle = pbefore->Next;
    pafter = pmiddle->Next;

    NUMKEYS first_half_subtree_key_count = 0;
    if (IsLeaf(PagePtr))
        first_half_subtree_key_count = FirstHalfNumKeys;
    else {
        struct KeyRecord *p = PagePtr->KeyListPtr;
        while (true) {
            struct PageHdr *page = FetchPage(p->PgNum);
            first_half_subtree_key_count += page->SubtreeKeyCount;
            FreePage(page);

            if (p == pmiddle)
                break;
            p = p->Next;
        };
    }

    /* Install the header of new page */
    newPagePtr = (struct PageHdr *) malloc(sizeof(struct PageHdr));
    ck_malloc(newPagePtr, "newPagePtr");
    newPagePtr->PgTypeID = PagePtr->PgTypeID;
    newPagePtr->PgNum = getNewPageNum();
    if (IsLeaf(newPagePtr))
        newPagePtr->PgNumOfNxtLfPg = PagePtr->PgNumOfNxtLfPg;
    if (IsNonLeaf(newPagePtr))
        newPagePtr->PtrToFinalRtgPg = PagePtr->PtrToFinalRtgPg;

    newPagePtr->SubtreeKeyCount = PagePtr->SubtreeKeyCount - first_half_subtree_key_count;
    PagePtr->SubtreeKeyCount = first_half_subtree_key_count;

    /* Transfer the keys of second half of page to new page */
    newPagePtr->KeyListPtr = pafter;
    /* Adjust the last ptr of first half of page to be null */
    if (IsLeaf(PagePtr)) {
        pmiddle->Next = NULL; /* the middle key stays on the leaf */
    } else {
        pbefore->Next = NULL; /* This way we have a proper B+ tree */
    }

    /* Adjust the header of page being split */
    if (IsLeaf(PagePtr))
        PagePtr->PgNumOfNxtLfPg = newPagePtr->PgNum;
    if (IsNonLeaf(PagePtr))
        PagePtr->PtrToFinalRtgPg = pmiddle->PgNum;

    /* Create an "upKey" node for the middle key */
    upk = (struct upKey *) malloc(sizeof(struct upKey));
    ck_malloc(upk, "upk");
    upk->left = PagePtr->PgNum;
    upk->right = newPagePtr->PgNum;
    upk->key = strsave(pmiddle->StoredKey);
    /* -christos-: modify this portion, with "struct upKey" -DONE! */

    FlushPage(PagePtr);
    FlushPage(newPagePtr);

    return (upk);
}
