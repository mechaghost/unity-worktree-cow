"""Clone data and publish replacement caches using native macOS operations."""
import ctypes
import os
import stat
import sys

CLONE_NOFOLLOW = 0x0001
CLONE_ACL = 0x0004
COPYFILE_METADATA = 0x0007
RENAME_SWAP = 0x00000002
RENAME_EXCL = 0x00000004

libc = ctypes.CDLL(None, use_errno=True)
clonefile = libc.clonefile
clonefile.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int)
clonefile.restype = ctypes.c_int
copyfile = libc.copyfile
copyfile.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_uint)
copyfile.restype = ctypes.c_int
renamex = libc.renamex_np
renamex.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
renamex.restype = ctypes.c_int


def checked(result, source, destination):
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), f"{source} -> {destination}")


def clone_tree(source, destination):
    mode = os.lstat(source).st_mode
    src = os.fsencode(source)
    dst = os.fsencode(destination)
    if stat.S_ISDIR(mode):
        os.mkdir(destination)
        with os.scandir(source) as entries:
            for entry in entries:
                clone_tree(entry.path, os.path.join(destination, entry.name))
        checked(copyfile(src, dst, None, COPYFILE_METADATA), source, destination)
    elif stat.S_ISREG(mode) or stat.S_ISLNK(mode):
        checked(clonefile(src, dst, CLONE_NOFOLLOW | CLONE_ACL), source, destination)
    else:
        raise ValueError(f"Unsupported file type: {source}")


def main():
    operation, source, destination = sys.argv[1:]
    if operation == "clone":
        clone_tree(source, destination)
        return
    flags = {"swap": RENAME_SWAP, "publish": RENAME_EXCL}[operation]
    checked(renamex(os.fsencode(source), os.fsencode(destination), flags), source, destination)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))
