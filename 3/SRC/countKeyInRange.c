#include "def.h"

extern PAGENO treesearch_page(PAGENO PageNo, char *key);
extern POSTINGSPTR treesearch(PAGENO PageNo, char *key);
extern int FindInsertionPosition(struct KeyRecord *KeyListTraverser, char *Key,
				 int *Found, NUMKEYS NumKeys, int Count);
extern PAGENO FindPageNumOfChild(struct PageHdr *PagePtr,
                                 struct KeyRecord *KeyListTraverser, char *Key,
                                 NUMKEYS NumKeys);
extern struct PageHdr *FetchPage(PAGENO Page);
extern int strtolow(char *s);

NUMKEYS countKeyInRange(char *leftKey, char *rightKey) {
    //implement me :)
    return 0;
}

