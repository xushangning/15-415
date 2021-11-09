#include "def.h"

extern FILE *fpbtree;
extern int btReadCount; /* counts the number of b-tree page reads */

/**
 * The function FetchPage reads a page from disk using the formula
 * PageNum * PAGESIZE - PAGESIZE, e.g., if the PageNum = 3 and
 * PAGESIZE = 1024, the B-Tree file will be accessed starting at offset 2048,
 * wherein the first page would be stored at offset 0, and the second page at
 * offset 1024.
 *
 * @param Page Page number of page to be fetched
 * @return
 */
struct PageHdr *FetchPage(PAGENO Page)
{
    struct PageHdr *PagePtr;
    struct KeyRecord *KeyNode,
        *KeyListTraverser; /* To traverse the list of keys */

    int i;
    PAGENO FindNumPagesInTree(void);

    /* check validity of "Page" */
    if ((Page < 1) || (Page > FindNumPagesInTree())) {
        printf("FetchPage: Pagenum %d out of range (%d,%d)\n", (int) Page,
               (int) ROOT, (int) FindNumPagesInTree());
        /*	exit(-1); */
    }

    /* Read in the page header */
    PagePtr = (struct PageHdr *) malloc(sizeof(*PagePtr));
    ck_malloc(PagePtr, "PagePtr");
    fseek(fpbtree, (long) Page * PAGESIZE - PAGESIZE, 0);

    fread(&PagePtr->PgTypeID, sizeof(char), 1, fpbtree);
    fread(&PagePtr->PgNum, sizeof(PagePtr->PgNum), 1, fpbtree);
    if ((PagePtr->PgNum) != Page) {
        printf("FetchPage: corrupted Page %d\n", (int) Page);
        exit(-1);
    }

    if (IsLeaf(PagePtr))
        fread(&PagePtr->PgNumOfNxtLfPg, sizeof(PagePtr->PgNumOfNxtLfPg), 1,
              fpbtree);
    fread(&PagePtr->NumBytes, sizeof(PagePtr->NumBytes), 1, fpbtree);
    fread(&PagePtr->NumKeys, sizeof(PagePtr->NumKeys), 1, fpbtree);
    fread(&PagePtr->SubtreeKeyCount, sizeof(PagePtr->SubtreeKeyCount), 1, fpbtree);
    PagePtr->KeyListPtr = NULL;
    if (IsNonLeaf(PagePtr))
        fread(&PagePtr->PtrToFinalRtgPg, sizeof(PagePtr->PtrToFinalRtgPg), 1,
              fpbtree);

    /* Read in the keys */
    KeyListTraverser = NULL;
    for (i = 0; i < PagePtr->NumKeys; i++) {
        KeyNode = (struct KeyRecord *) malloc(sizeof(*KeyNode));
        ck_malloc(KeyNode, "KeyNode");
        if (IsNonLeaf(PagePtr))
            fread(&KeyNode->PgNum, sizeof(KeyNode->PgNum), 1, fpbtree);
        fread(&KeyNode->KeyLen, sizeof(KeyNode->KeyLen), 1, fpbtree);
        KeyNode->StoredKey = (char *) malloc((KeyNode->KeyLen) + 1);
        ck_malloc(KeyNode->StoredKey, "KeyNode->StoredKey in FetchPage()");
        fread(KeyNode->StoredKey, sizeof(char), KeyNode->KeyLen, fpbtree);
        (*(KeyNode->StoredKey + KeyNode->KeyLen)) =
            '\0'; /* string terminator */
        if (IsLeaf(PagePtr))
            fread(&KeyNode->Posting, sizeof(KeyNode->Posting), 1, fpbtree);
        if (KeyListTraverser == NULL) {
            KeyListTraverser = KeyNode;
            PagePtr->KeyListPtr = KeyNode;
        } else {
            KeyListTraverser->Next = KeyNode;
            KeyListTraverser = KeyListTraverser->Next;
        }
    }
    if (PagePtr->NumKeys != 0)
        KeyListTraverser->Next = NULL;

    btReadCount++;
    return (PagePtr);
}
