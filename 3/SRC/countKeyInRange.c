#include "def.h"

extern PAGENO treesearch_page(PAGENO PageNo, const char *key);
extern POSTINGSPTR treesearch(PAGENO PageNo, char *key);
extern PAGENO FindPageNumOfChild(struct PageHdr *PagePtr,
                                 struct KeyRecord *KeyListTraverser, char *Key,
                                 NUMKEYS NumKeys);
extern int strtolow(char *s);

/**
 * Find the KeyRecord whose PgNum contains key.
 *
 * @param head
 * @param key
 * @return NULL if the key is in the last page
 */
struct KeyRecord *FindPage(struct KeyRecord *head, const char *key) {
  // Find the first KeyRecord not less than key.
  while (head && strcmp(head->StoredKey, key) < 0)
    head = head->Next;
  return head;
}

NUMKEYS NaiveCountKeyInRange(const char *leftKey, const char *rightKey) {
  PAGENO left = treesearch_page(ROOT, leftKey);
  // First, page points to the leaf node that should contain leftKey.
  struct PageHdr *page = FetchPage(left);
  struct KeyRecord *r;
  NUMKEYS count = 0, temp_count = 0;
  // Count the number of keys less than leftKey in the node.
  for (r = page->KeyListPtr; r && strcmp(r->StoredKey, leftKey) < 0; r = r->Next)
    ++temp_count;

  PAGENO right = strcmp(leftKey, rightKey) ? treesearch_page(ROOT, rightKey) : left;
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

NUMKEYS countKeyInRange(char *leftKey, char *rightKey) {
  if (strcmp(leftKey, rightKey) > 0)
    return 0;

  // Lowest Common Ancestor
  struct PageHdr *lca = FetchPage(ROOT);
  // Root page empty.
  if (lca->NumKeys == 0)
    return 0;

  struct KeyRecord *r;
  // Find the LCA.
  // When the loop exits and lca doesn't point to a leaf, r points to the
  // KeyRecord whose PgNum contains leftKey.
  while (IsNonLeaf(lca)) {
    r = FindPage(lca->KeyListPtr, leftKey);

    PAGENO page_no;
    if (r == NULL)
      page_no = lca->PtrToFinalRtgPg;
    else if (strcmp(rightKey, r->StoredKey) <= 0)
      page_no = r->PgNum;
    else
      break;

    FreePage(lca);
    lca = FetchPage(page_no);
  }

  NUMKEYS ret = 0;
  if (IsLeaf(lca)) {
    // count the number of keys in the leaf between leftkey and rightkey.
    for (r = lca->KeyListPtr; r && strcmp(r->StoredKey, leftKey) < 0; r = r->Next);
    while (r && strcmp(r->StoredKey, rightKey) <= 0) {
      r = r->Next;
      ++ret;
    }
  } else {
    struct KeyRecord *left = r, *right;
    // Number of pages between left and right, both exclusive
    NUMKEYS nInnerPages = 0;
    for (right = left->Next; right && strcmp(right->StoredKey, rightKey) < 0; right = right->Next)
      ++nInnerPages;
    // right == NULL when rightKey is in the last page.

    struct PageHdr *left_page = FetchPage(left->PgNum),
      *right_page = FetchPage(right ? right->PgNum : lca->PtrToFinalRtgPg),
      *page;
    // count which range require more page fetch, the middle or both sides.
    if (nInnerPages <= lca->NumKeys - 1 - nInnerPages) {
      for (r = left->Next; r != right; r = r->Next) {
        page = FetchPage(r->PgNum);
        ret += page->SubtreeKeyCount;
        FreePage(page);
      }
    } else {
      ret = lca->SubtreeKeyCount - left_page->SubtreeKeyCount - right_page->SubtreeKeyCount;
      for (r = lca->KeyListPtr; r != left; r = r->Next) {
        page = FetchPage(r->PgNum);
        ret -= page->SubtreeKeyCount;
        FreePage(page);
      }
      if (right) {
        for (r = right->Next; r; r = r->Next) {
          page = FetchPage(r->PgNum);
          ret -= page->SubtreeKeyCount;
          FreePage(page);
        }
        page = FetchPage(lca->PtrToFinalRtgPg);
        ret -= page->SubtreeKeyCount;
        FreePage(page);
      }
    }

    // count left range
    while (IsNonLeaf(left_page)) {
      // Not NumKeys + 1 because not counting the page whose corresponding
      // subtree may contain leftKey in advance.
      nInnerPages = left_page->NumKeys;
      for (left = left_page->KeyListPtr; left && strcmp(left->StoredKey, leftKey) < 0; left = left->Next)
        --nInnerPages;

      struct PageHdr *next_left_page = FetchPage(left ? left->PgNum : left_page->PtrToFinalRtgPg);
      if (nInnerPages <= left_page->NumKeys - nInnerPages) {
        if (left) {
          for (r = left->Next; r; r = r->Next) {
            page = FetchPage(r->PgNum);
            ret += page->SubtreeKeyCount;
            FreePage(page);
          }
          page = FetchPage(left_page->PtrToFinalRtgPg);
          ret += page->SubtreeKeyCount;
          FreePage(page);
        }
      } else {
        ret += left_page->SubtreeKeyCount - next_left_page->SubtreeKeyCount;
        for (r = left_page->KeyListPtr; r != left; r = r->Next) {
          page = FetchPage(r->PgNum);
          ret -= page->SubtreeKeyCount;
          FreePage(page);
        }
      }

      FreePage(left_page);
      left_page = next_left_page;
    }
    // Now left_page is a leaf.
    ret += left_page->SubtreeKeyCount;
    for (r = left_page->KeyListPtr; r && strcmp(r->StoredKey, leftKey) < 0; r = r->Next)
      --ret;
    FreePage(left_page);

    // count right range
    while (IsNonLeaf(right_page)) {
      nInnerPages = 0;
      for (right = right_page->KeyListPtr; right && strcmp(right->StoredKey, rightKey) < 0; right = right->Next)
        ++nInnerPages;

      struct PageHdr *next_right_page = FetchPage(right ? right->PgNum : right_page->PtrToFinalRtgPg);
      if (nInnerPages <= right_page->NumKeys - nInnerPages) {
        for (r = right_page->KeyListPtr; r != right; r = r->Next) {
          page = FetchPage(r->PgNum);
          ret += page->SubtreeKeyCount;
          FreePage(page);
        }
      } else {
        ret += right_page->SubtreeKeyCount - next_right_page->SubtreeKeyCount;
        if (right) {
          for (r = right->Next; r; r = r->Next) {
            page = FetchPage(r->PgNum);
            ret += page->SubtreeKeyCount;
            FreePage(page);
          }
          page = FetchPage(right_page->PtrToFinalRtgPg);
          ret -= page->SubtreeKeyCount;
          FreePage(page);
        }
      }

      FreePage(right_page);
      right_page = next_right_page;
    }
    // Now right_page is a leaf.
    for (r = right_page->KeyListPtr; r && strcmp(r->StoredKey, rightKey) <= 0; r = r->Next)
      ++ret;
    FreePage(right_page);
  }
  FreePage(lca);

#ifndef NDEBUG
  NUMKEYS count = NaiveCountKeyInRange(leftKey, rightKey);
  assert(ret == count);
#endif
  return ret;
}

