import random
import string
import uuid

from faker import Faker

try:
    from tqdm import tqdm

    progressbar = True
except:
    print("skipping progress bar")
    progressbar = False

fake = Faker()

datatypes = ["bool", "int", "float", "str", "list", "word", "text", "date", "uuid", "id", "name"]


def generate_bool(null_probability=None):
    """
    returns True|False|None*
    None is only a possible outcome if null_probability is set
    """
    if null_probability and random.random() < null_probability:
        return None
    return random.choice([True, False])


def generate_int(min_value=0, max_value=100, null_probability=None):
    """
    returns integer between min_value and max_value parameters or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    min_value : minimum value of possible return value
    max_value : maximum value of possible return value
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    if null_probability and random.random() < null_probability:
        return None
    min_value = int(min_value)
    max_value = int(max_value)
    return random.randint(min_value, max_value)


def generate_float(min_value=0.0, max_value=1.0, null_probability=None):
    """
    returns float between min_value and max_value parameters or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    min_value : minimum value of possible return value
    max_value : maximum value of possible return value
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    if null_probability and random.random() < null_probability:
        return None
    return random.uniform(min_value, max_value)


def generate_from_list(values, weights=None, null_probability=None):
    """
    returns value from the list or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    values: list of tuples (value,weight) or list of values to provide return value from
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    if isinstance(values, str):
        try:
            values = eval(values)
        except Exception as e:
            print(
                'values string "{values}" could not be converted to a list, it should be in form [a,b,c,d]'
            )
            print("The error is: ", e)
    assert isinstance(values, list)
    if null_probability and random.random() < null_probability:
        return None
    if weights:
        if isinstance(weights, str):
            try:
                weights = eval(weights)
            except Exception as e:
                print(
                    'weights string "{weights}" could not be converted to a list, it should be in form [0.1,0.9]'
                )
                print("The error is: ", e)
        assert isinstance(weights, list)
        assert len(weights) == len(values)
        return random.choices(values, weights=weights, k=1)[0]
    else:
        return random.choice(values)


def generate_str(length=8, characters=string.ascii_lowercase, null_probability=None):
    """
    returns string of given length of characters from the list of characters or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    length : length of string to return
    characters : (default=string.ascii_lowercase) string of characters to select from,
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    assert isinstance(characters, str)
    if null_probability and random.random() < null_probability:
        return None
    return "".join(random.choices(characters, k=int(length)))


def generate_word(null_probability=None):
    """
    returns a word from Faker or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    if null_probability and random.random() < null_probability:
        return None
    return fake.word()


def generate_text(length=20, null_probability=None):
    """
    returns a text string from Faker with given length or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    length: (default=20) length of string of text
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    length = int(length)
    if null_probability and random.random() < null_probability:
        return None
    return fake.text(length)


def generate_date(start_date="-1y", end_date="today", null_probability=None):
    """
    returns a date from Faker with given length or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    start_date: (default='-1y')
    end_date: (cdefault='today')
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    if null_probability and random.random() < null_probability:
        return None
    return fake.date_between(start_date=start_date, end_date=end_date)


def generate_uuid(null_probability=None):
    if null_probability and random.random() < null_probability:
        return None
    return str(uuid.uuid4())


def generate_name(null_probability=None):
    """
    returns a word from Faker or None
    None is only a possible outcome if null_probability is set

    parameters:
    -----------
    null_probability: (optional) set to value between 0.0 and 1.0 if None value is to be included as a possible return value
    """
    if null_probability and random.random() < null_probability:
        return None
    return fake.name()


def infer_datatype(**options):
    if "min_value" in options:
        if isinstance(options["min_value"], int):
            return "int"
        if isinstance(options["min_value"], float):
            return "float"
    if "values" in options:
        if isinstance(options["values"], list):
            return "list"
    if "length" in options:
        return "str" if options["length"] <= 8 else "text"
    if "start_date" in options:
        return "date"
    return None


class Generator:
    def __init__(self, name, datatype, **options):
        options = {k: v for k, v in options.items() if v != None}
        if datatype == "infer":
            datatype = infer_datatype(**options)
        assert datatype in datatypes
        # if 'null_probability' in options:
        #     assert(options['null_probability'] <= 1.0 and options['null_probability'] >= 0.0)
        self.name = name if name else generate_str()
        self.datatype = datatype
        self.generate_function = {
            "bool": generate_bool,
            "int": generate_int,
            "float": generate_float,
            "str": generate_str,
            "list": generate_from_list,
            "word": generate_word,
            "text": generate_text,
            "date": generate_date,
            "uuid": generate_uuid,
            "name": generate_name,
            "id": None,
        }[datatype]

        if self.datatype == "id":
            self.id_increment = options["increment"] if "increment" in options else 1
            # if the first value returned is the start_value we need to set this at 1 increment less
            self.id = (
                options["start_value"] if "start_value" in options else 0
            ) - self.id_increment

        self.options = options

    #
    @property
    def value(self):
        if self.datatype == "id":
            self.id += self.id_increment
            return self.id
        else:
            return self.generate_function(**self.options)


def generate_row(generators) -> dict:
    row = {}
    for generator in generators:
        row[generator.name] = generator.value
    return row


def generate_rows(generators, num_rows, bar=None) -> None:
    row_count = 0
    if bar:
        bar.progress(0)
    while row_count < num_rows:
        row = generate_row(generators)
        row_count += 1
        yield row
        if bar:
            bar.progress(row_count / num_rows)
    if bar:
        bar.progress(100)
