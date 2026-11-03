import os

"""
The error object uses the class ErrorTrap to store the errors during the read and write process
ex. bin_data = open_file('bin_data.bin') 
-> False # Error because the file was not found

It's possible read exactly the error raised using:
error.get_last_error() -> '[Errno 2] No such file or directory: 'bin_data.bin'' # str
error.get_errors() -> [[Errno 2] No such file or directory: 'bin_data.bin']     # list with the last errors
error.error -> same as error.get_errors()

Note: 
if you are using the import file_io as fio, then use: fio.open_file, fio.error...
"""



class ErrorTrap:
    def __init__(self, error=''):
        self.error = []
        if error:
            self.error.append(error)

    def set_error(self, error: str):
        self.error.append(error)

    def get_errors(self) -> list:
        return self.error

    def get_last_error(self) -> str:
        if self.error:
            return self.error[-1]
        return 'Error reading file'

    def clear_error_list(self):
        self.error = []

error_trap = ErrorTrap()


def save_file(file_name: str, data: bin) -> bool:
    """
    ex: save_file('output.bin', b'this is a test')
    -> True
    """
    global error_trap
    try:
        with open(file_name, 'wb') as data_obj:
            data_obj.write(data)
    except Exception as e:
        error_trap.set_error(e)
        return False
    return True


def open_split(file_name: str, seek=[0], length=[0]) -> list:
    """
    ex: open_split('bin_data.bin', [0, 10, 20], [10, 10, 0)
    -> [b'8ds..fd', b'8s9..89d', b'fd9..9d']
    (*) length = 0 means until the end
    """
    global error_trap
    if os.path.exists(file_name):
        file_size = os.path.getsize(file_name)
    data = []
    try:
        with open(file_name, 'rb') as data_obj:
            for s, l in zip(seek, length):
                if l <= 0:
                    l = file_size - s
                data_obj.seek(s)
                data.append(data_obj.read(l))
    except Exception as e:
        error_trap.set_error(e)
        return ['' for i in range(len(seek))]
    return data


def open_file(file_name: str, length=0) -> bin:
    """
    ex. open_file('test.bin')
    -> b'af0s9f'
    """
    global error_trap
    try:
        with open(file_name, 'rb') as data_obj:
            if length > 0:
                data = data_obj.read(length)
            else:
                data = data_obj.read()
    except Exception as e:
        error_trap.set_error(e)
        return b''
    return data
