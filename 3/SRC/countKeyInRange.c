#include "def.h"

extern PAGENO treesearch_page(PAGENO PageNo, char *key);
extern POSTINGSPTR treesearch(PAGENO PageNo, char *key);
extern PAGENO FindPageNumOfChild(struct PageHdr *PagePtr,
                                 struct KeyRecord *KeyListTraverser, char *Key,
                                 NUMKEYS NumKeys);
extern int strtolow(char *s);

NUMKEYS countKeyInRange(char *leftKey, char *rightKey) {
  int strcmp_result;
  if ((strcmp_result = strcmp(leftKey, rightKey)) > 0)
    return 0;

  PAGENO left = treesearch_page(ROOT, leftKey);
  // First, page points to the leaf node that should contain leftKey.
  struct PageHdr *page = FetchPage(left);
  struct KeyRecord *r;
  NUMKEYS count = 0, temp_count = 0;
  // Count the number of keys less than leftKey in the node.
  for (r = page->KeyListPtr; r && strcmp(r->StoredKey, leftKey) < 0; r = r->Next)
    ++temp_count;

  PAGENO right = strcmp_result ? treesearch_page(ROOT, rightKey) : left;
  // Sum the number of keys from leftKey's node to the node right before
  // rightKey's node.
  for (PAGENO page_no = page->PgNum; page_no != right; page = FetchPage(page_no)) {
    count += page->NumKeys;
    page_no = page->PgNumOfNxtLfPg;
    FreePage(page);
  }
  // After the loop, page points to rightKey's node.

  // When leftKey and rightKey resides in the same node, there is no need to
  // change r as it points to the first key not less than leftKey and we can
  // directly use it for counting keys.
  if (left != right) {
    count -= temp_count;
    r = page->KeyListPtr;
  }
  // Count the number of keys not greater than rightKey in its node.
  for (; r && strcmp(r->StoredKey, rightKey) <= 0; r = r->Next)
    ++count;

  FreePage(page);
  return count;
}

