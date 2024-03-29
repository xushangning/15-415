/***************************************************************************
*                                                                          *
*   This function inserts a key into a leaf page, after a Posting has      *
*   been created.  In the case where a key is already stored in the        *
*   B-Tree, the Posting record is updated.                                 *
    If the page overflows, it
       splits it,
       flushes the two new pages and
       return the value of the middle key in a structure "upKey"
    Otherwise, it just flushes back the old page and returns NULL
*                                                                          *
***************************************************************************/

#include "def.h"

extern void UpdatePostingsFile(POSTINGSPTR *pPostOffset, TEXTPTR NewTextOffset);
extern int CreatePosting(TEXTPTR TextOffset, POSTINGSPTR *pPostOffset);
extern int fillIn(struct PageHdr *PagePtr);

struct upKey *InsertKeyInLeaf(struct PageHdr *PagePtr, char *Key,
                              TEXTPTR TextOffset, bool *duplicate_key) {
    struct KeyRecord *KeyListTraverser, /*                              */
        *KeyListTrailer,                /* Pointers to the list of keys */
        *NewKeyNode;

    int InsertionPosition, /* Position for insertion */
        Count, i;
    POSTINGSPTR PostOffset;
    struct upKey *MiddleKey;
    char *strsave(char *s);

    Count = 0;

    /* Find insertion position */
    KeyListTraverser = PagePtr->KeyListPtr;
    InsertionPosition = FindInsertionPosition(KeyListTraverser, Key, duplicate_key,
                                              PagePtr->NumKeys, Count);

    /* Key is already in the B-Tree */
    if (*duplicate_key) {

        POSTINGSPTR oldpointer;
        /* printf ("Key = %s\n", Key);
        printf ("  Text Offsets are:\n");  */
        for (i = 0; i < InsertionPosition - 1; i++)
            KeyListTraverser = KeyListTraverser->Next;
        /* change made here by Frank Andrasco
           since postings pointer may change, pointer must be passed by
           reference
           instead of by value  */

        oldpointer = KeyListTraverser->Posting;
        UpdatePostingsFile(&KeyListTraverser->Posting, TextOffset);
        /* check to see if posting value changed, if so rewrite to disk */
        if (KeyListTraverser->Posting == oldpointer)
            FreePage(PagePtr);
        else
            FlushPage(PagePtr);

        return (NULL);
    }

    /* Key must be inserted in B-Tree */
    CreatePosting(TextOffset, &PostOffset);
    /* Traverse the list of keys to insertion position */
    KeyListTraverser = PagePtr->KeyListPtr;
    for (i = 0; i < InsertionPosition; i++) {
        KeyListTrailer = KeyListTraverser;
        KeyListTraverser = KeyListTraverser->Next;
    }

    /* Create a new node for the new key and insert key informtion */
    NewKeyNode = (struct KeyRecord *) malloc(sizeof(*NewKeyNode));
    ck_malloc(NewKeyNode, "NewKeyNode");
    NewKeyNode->KeyLen = strlen(Key);
    NewKeyNode->StoredKey = strsave(Key);
    NewKeyNode->Posting = PostOffset;

    /* Insert new key in list */
    if (InsertionPosition == 0) {
        PagePtr->KeyListPtr = NewKeyNode;
    } else
        KeyListTrailer->Next = NewKeyNode;
    /* Link new key to keys that lexicographically follow it */
    NewKeyNode->Next = KeyListTraverser;

    /* Update page header information */
    fillIn(PagePtr);

    ++PagePtr->SubtreeKeyCount;

    /* split page, if necessary, and flush */
    if (PagePtr->NumBytes <= PAGESIZE) {
        FlushPage(PagePtr);
        return (NULL);
    } else {
        MiddleKey = SplitPage(PagePtr);
        return (MiddleKey);
    }
}
