"""
Tests for the token-level diff. Check that the modified diff-match-patch
is returning what we expect for deletion, insertion, and substitution.
"""
from revisions import diff_wordMode


def test_deletes():
    # Delete at the end 
    assert diff_wordMode(
        "This should show something being deleted", 
        "This should show something being", return_offsets=False) \
            == [(0, 'This should show something being '), (-1, 'deleted ')]
    
    # Delete in the middle
    assert diff_wordMode(
        "Deletion in the middle", 
        "Deletion in middle", return_offsets=False) \
            == [(0, 'Deletion in '), (-1, 'the '), (0, 'middle ')]
    
    
def test_inserts():
    # Insert at the end
    assert diff_wordMode(
        "Insertion at the end", 
        "Insertion at the end here", return_offsets=False) \
            == [(0, 'Insertion at the end '), (1, 'here ')]
    
    # Insert in the middle
    assert diff_wordMode(
        "Insertion in the middle", 
        "Insertion here in the middle", return_offsets=False) \
            == [(0, 'Insertion '), (1, 'here '), (0, 'in the middle ')]
    

def test_substitutes():
    # Subtitute at the end with overlapping chars
    assert diff_wordMode(
        "Now here we have a substitution", 
        "Now here we have a substitute", return_offsets=False) \
            == [(0, 'Now here we have a '), (-1, 'substitution '), (1, 'substitute ')]
    
    # Substitute at the end with no overlapping chars 
    assert diff_wordMode(
        "Now this is another sub", 
        "Now this is another lam", return_offsets=False) \
            == [(0, 'Now this is another '), (-1, 'sub '), (1, 'lam ')]
    
    # Substitute in the middle with overlapping chars 
    assert diff_wordMode(
        "Substitution in the middle", 
        "Substitution in ze middle", return_offsets=False) \
            == [(0, 'Substitution in '), (-1, 'the '), (1, 'ze '), (0, 'middle ')]
    
    # Substitute in the middle with no overlapping chars 
    assert diff_wordMode(
        "Substitution in the middle",
        "Substitution in a middle", return_offsets=False) \
            == [(0, 'Substitution in '), (-1, 'the '), (1, 'a '), (0, 'middle ')]

