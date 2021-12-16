#include "def.h"

extern PAGENO treesearch_page(PAGENO PageNo, const char *key);
extern POSTINGSPTR treesearch(PAGENO PageNo, char *key);
extern PAGENO FindPageNumOfChild(struct PageHdr *PagePtr,
                                 struct KeyRecord *KeyListTraverser, char *Key,
                                 NUMKEYS NumKeys);
extern int strtolow(char *s);

/**
 * Find the first KeyRecord whose StoredKey is not less than the given key.
 *
 * @details
 * If we assume that the given key is in the subtree rooted at the page which
 * contains head and the page is a leaf page, then the returned KeyRecord has
 * StoredKey == key. If we make the same assumption and the page is not a leaf
 * page, then the returned KeyRecord's PgNum corresponds to the page that
 * contains the given key.
 *
 * @param head
 * @param key
 * @param[out] count The number of keys before the given key.
 * @return NULL if the key is in the last page
 */
struct KeyRecord *KeyRecordLowerBound(struct KeyRecord *head, const char *key, NUMKEYS *count) {
  NUMKEYS temp_count = 0;
  while (head && strcmp(head->StoredKey, key) < 0) {
    ++temp_count;
    head = head->Next;
  }
  if (count)
    *count = temp_count;
  return head;
}

/**
 * Find the first KeyRecord whose StoredKey is greater than the given key.
 *
 * @param head
 * @param key
 * @param count
 * @return
 * @sa KeyRecordLowerBound(struct KeyRecord *head, const char *key, NUMKEYS *count)
 */
struct KeyRecord *KeyRecordUpperBound(struct KeyRecord *head, const char *key, NUMKEYS *count) {
  NUMKEYS temp_count = 0;
  while (head && strcmp(head->StoredKey, key) <= 0) {
    ++temp_count;
    head = head->Next;
  }
  if (count)
    *count = temp_count;
  return head;
}

NUMKEYS NaiveCountKeyInRange(const char *leftKey, const char *rightKey) {
  PAGENO left = treesearch_page(ROOT, leftKey);
  // First, page points to the leaf node that should contain leftKey.
  struct PageHdr *page = FetchPage(left);
  struct KeyRecord *r;
  NUMKEYS count = 0, temp_count = 0;
  r = KeyRecordLowerBound(page->KeyListPtr, leftKey, &temp_count);

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

  KeyRecordUpperBound(r, rightKey, &temp_count);
  count += temp_count;

  FreePage(page);
  return count;
}

NUMKEYS countKeyInRange(char *leftKey, char *rightKey) {
  strtolow(leftKey);
  strtolow(rightKey);
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
    r = KeyRecordLowerBound(lca->KeyListPtr, leftKey, NULL);

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
    r = KeyRecordLowerBound(lca->KeyListPtr, leftKey, NULL);
    KeyRecordUpperBound(r, rightKey, &ret);
  } else {
    struct KeyRecord *left = r, *right;
    // Number of pages between left and right, both exclusive
    NUMKEYS nInnerPages = 0;
    right = KeyRecordLowerBound(left->Next, rightKey, &nInnerPages);
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
      NUMKEYS temp_count = 0;
      left = KeyRecordLowerBound(left_page->KeyListPtr, leftKey, &temp_count);
      // Not NumKeys + 1 because not counting the page whose corresponding
      // subtree may contain leftKey in advance.
      nInnerPages = left_page->NumKeys - temp_count;

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
    NUMKEYS temp_count = 0;
    r = KeyRecordLowerBound(left_page->KeyListPtr, leftKey, &temp_count);
    ret += left_page->SubtreeKeyCount - temp_count;
    FreePage(left_page);

    // count right range
    while (IsNonLeaf(right_page)) {
      nInnerPages = 0;
      right = KeyRecordLowerBound(right_page->KeyListPtr, rightKey, &nInnerPages);

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
            ret -= page->SubtreeKeyCount;
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
    KeyRecordUpperBound(right_page->KeyListPtr, rightKey, &temp_count);
    ret += temp_count;
    FreePage(right_page);
  }
  FreePage(lca);

#ifndef NDEBUG
  NUMKEYS count = NaiveCountKeyInRange(leftKey, rightKey);
  assert(ret == count);
#endif
  return ret;
}

