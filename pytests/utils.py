import filecmp
import os
from filecmp import dircmp


def is_same(dir1, dir2):
    """
    Compare two directory trees content.
    Return False if they differ, True is they are the same.
    """
    compared = dircmp(dir1, dir2)
    if (compared.left_only or compared.right_only or compared.diff_files
            or compared.funny_files):
        return False
    for subdir in compared.common_dirs:
        if not is_same(os.path.join(dir1, subdir), os.path.join(dir2, subdir)):
            return False
    return True

def are_dir_trees_equal(dir1, dir2):
    comparison = filecmp.dircmp(dir1, dir2)
    if len(comparison.right_only) != 0:
        return [os.path.join(dir1, x) for x in comparison.right_only]
    if len(comparison.funny_files) != 0:
        return [os.path.join(dir1, x) for x in comparison.funny_files]

    (_, mismatch, errors) =  filecmp.cmpfiles(
        dir1, dir2, comparison.common_files, shallow=False)
    if len(mismatch) != 0:
        if os.environ.get('correct-errors', 'False') == 'True':
            for x in mismatch:
                with open(os.path.join(dir1, x), 'r') as src:
                    with open(os.path.join(dir2, x), 'w') as dst:
                        a = src.read()
                        dst.write(a)
        else:
            return [os.path.join(dir1, x) for x in mismatch]
    if len(errors) != 0:
        return [os.path.join(dir1, x) for x in errors]

    res = []
    for common_dir in comparison.common_dirs:
        new_dir1 = os.path.join(dir1, common_dir)
        new_dir2 = os.path.join(dir2, common_dir)
        res += are_dir_trees_equal(new_dir1, new_dir2)

    return res