import pyewf
import pytsk3
import hashlib

class EWFImgInfo(pytsk3.Img_Info):
    def __init__(self, ewf_handle):
        self._ewf_handle = ewf_handle
        self._size = ewf_handle.get_media_size()
        super().__init__(url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

    def close(self):
        self._ewf_handle.close()

    def read(self, offset, size):
        self._ewf_handle.seek(offset)
        return self._ewf_handle.read(size)

    def get_size(self):
        return self._size

def open_image(image_file):
    filenames = pyewf.glob(image_file)
    ewf_handle = pyewf.handle()
    ewf_handle.open(filenames)
    return ewf_handle

def calculate_md5(file_entry):
    hasher = hashlib.md5()
    file_size = file_entry.info.meta.size

    offset = 0
    while offset < file_size:
        available_to_read = min(1024*1024, file_size - offset)
        data = file_entry.read_random(offset, available_to_read)
        hasher.update(data)
        offset += available_to_read

    return hasher.hexdigest().lower()

def load_hashset(hashset_file):
    with open(hashset_file, 'r') as f:
        return set(line.strip().lower() for line in f)

def print_directory_structure(directory, hash_set, indent=""):
    for entry in directory:
        filename = entry.info.name.name.decode('utf-8')

        if entry.info.meta is None:
            continue

        if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_REG:
            file_md5 = calculate_md5(entry)
            if file_md5 in hash_set:
                print(f"Match found: {filename} (MD5: {file_md5})")

        if entry.info.meta.type == pytsk3.TSK_FS_META_TYPE_DIR:
            if filename not in [".", ".."]:
                sub_directory = entry.as_directory()
                print_directory_structure(sub_directory, hash_set, indent + "    ")

def process_partition(fs, hash_set):
    try:
        root_dir = fs.open_dir(path="/")
        print_directory_structure(root_dir, hash_set)
    except IOError as e:
        print(f"Cannot open the file system: {e}")

def main(image_file, hashset_file):
    ewf_handle = open_image(image_file)
    hash_set = load_hashset(hashset_file)

    image_handle = EWFImgInfo(ewf_handle)

    try:
        # 다수 파티션일 확인
        partition_table = pytsk3.Volume_Info(image_handle)
        for partition in partition_table:
            if partition.len > 2048:  # 유효한 파티션인지 확인
                print(f"Partition {partition.addr}:")
                try:
                    fs = pytsk3.FS_Info(image_handle, offset=partition.start * 512)
                    process_partition(fs, hash_set)
                except IOError as e:
                    print(f"  Cannot open partition {partition.addr}: {e}")
    except IOError:
        # 단일 파티션 또는 파티션이 없는 경우 직접 파일 시스템을 열기
        print("No partition table found. Trying to open as a single partition.")
        try:
            fs = pytsk3.FS_Info(image_handle)
            process_partition(fs, hash_set)
        except IOError as e:
            print(f"Cannot open the file system: {e}")

if __name__ == "__main__":
    image_file = "/mnt/c/Users/light/Desktop/BoB/과제/유현 멘토님/과제 1/USB-8G.E01"
    hashset_file = "/mnt/c/Users/light/Desktop/BoB/과제/유현 멘토님/과제 1/hashset.txt"
    main(image_file, hashset_file)
