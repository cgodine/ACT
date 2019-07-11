# Here we define the methods for performing the tests and putting the
# results in the ancillary quality control varible. If you add a test
# to this file you will need to add a method reference in the main
# qcfilter class definition to make it callable.

import numpy as np
from act.utils import get_missing_value


def rolling_window(data, window):
    '''
    A function used by some test to efficiently calculate numpy
    statistics over a rolling window.

    Parameters
    ----------
    data : numpy array
        The data array to analyze
    window : int
        Number of data points to perform numpy statistics over

    Returns
    -------
        Will return a numpy array with a new dimension set to the window
        size. The numpy functions should then use -1 for dimension to
        reduce back to orginal data array size.

    Example
    -------
    > data = np.arange(10, dtype=np.float)
    > stdev = np.nanstd(rolling_window(data, 3), axis=-1)
    > stdev
    [0.81649658 0.81649658 0.5 1. 0.5 0.81649658 0.81649658 2.1602469]

    '''

    shape = data.shape[:-1] + (data.shape[-1] - window + 1, window)
    strides = data.strides + (data.strides[-1],)
    return np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)


def add_missing_value_test(self, var_name, missing_value=None,
                           missing_value_att_name='missing_value',
                           test_number=None, test_assessment='Bad',
                           test_meaning=None, flag_value=False,
                           prepend_text=None):
    '''
        Method to add indication in quality control variable
        where data value is set to missing value.

        Parameters
        ----------
        var_name : str
            Data variable name.
        missing_value : int or float
            Optional missing value to use. If not provided will attempt
            to get it from the variable attribute or use NaN.
        missing_value_att_name : str
            Optional attribute name to use.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    if test_meaning is None:
        test_meaning = 'Value is set to missing_value.'

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    if missing_value is None:
        missing_value = get_missing_value(self._obj, var_name, nodefault=True)
        if (missing_value is None and
                self._obj[var_name].values.dtype.type in
                (type(0.0), np.float16, np.float32, np.float64)):
            missing_value = float('nan')
        else:
            missing_value = -9999

    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        missing_value = float(missing_value)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        missing_value = int(missing_value)

    if np.isnan(missing_value) is False:
        data = np.ma.masked_equal(self._obj[var_name].values,
                                  missing_value)
    else:
        data = np.ma.masked_invalid(self._obj[var_name].values)

    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    test_dict = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)

    try:
        self._obj[var_name].attrs[missing_value_att_name]
    except KeyError:
        self._obj[var_name].attrs[missing_value_att_name] = missing_value

    return test_dict


def add_less_test(self, var_name, limit_value, test_meaning=None,
                  test_assessment='Bad', test_number=None,
                  flag_value=False, limit_attr_name=None,
                  prepend_text=None):
    '''
        Method to perform a less than test (i.e. minumum value) and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value : int or float
            Limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_name : str
            Optional attribute name to store the limit_value under
            quality control ancillary variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_name is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name = 'warn_min'
        else:
            attr_name = 'fail_min'
    else:
        attr_name = limit_attr_name

    if test_meaning is None:
        test_meaning = ('Data value less than {}.').format(attr_name)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = np.ma.masked_less(self._obj[var_name].values, limit_value)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    test_dict = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)

    # Ensure min value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value = float(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value = int(limit_value)

    self._obj[qc_var_name].attrs[attr_name] = limit_value

    return test_dict


def add_greater_test(self, var_name, limit_value, test_meaning=None,
                     test_assessment='Bad', test_number=None,
                     flag_value=False, limit_attr_name=None,
                     prepend_text=None):
    '''
        Method to perform a greater than test (i.e. maximum value) and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value : int or float
            Limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_name : str
            Optional attribute name to store the limit_value under
            quality control ancillary variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_name is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name = 'warn_max'
        else:
            attr_name = 'fail_max'
    else:
        attr_name = limit_attr_name

    if test_meaning is None:
        test_meaning = ('Data value greater than {}.').format(attr_name)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = np.ma.masked_greater(self._obj[var_name].values,
                                limit_value)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)
    # Ensure max value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value = float(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value = int(limit_value)

    self._obj[qc_var_name].attrs[attr_name] = limit_value

    return result


def add_less_equal_test(self, var_name, limit_value, test_meaning=None,
                        test_assessment='Bad', test_number=None,
                        flag_value=False, limit_attr_name=None,
                        prepend_text=None):
    '''
        Method to perform a less than or equal to test
        (i.e. minumum value) and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value : int or float
            Limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_name : str
            Optional attribute name to store the limit_value under
            quality control ancillary variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_name is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name = 'warn_min'
        else:
            attr_name = 'fail_min'
    else:
        attr_name = limit_attr_name

    if test_meaning is None:
        test_meaning = ('Data value less than '
                        'or equal to {}.').format(attr_name)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = np.ma.masked_less_equal(self._obj[var_name].values, limit_value)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)

    # Ensure min value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value = float(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value = int(limit_value)

    self._obj[qc_var_name].attrs[attr_name] = limit_value

    return result


def add_greater_equal_test(self, var_name, limit_value, test_meaning=None,
                           test_assessment='Bad', test_number=None,
                           flag_value=False, limit_attr_name=None,
                           prepend_text=None):
    '''
        Method to perform a less than or equal to test
        (i.e. minumum value) and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value : int or float
            Limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_name : str
            Optional attribute name to store the limit_value under
            quality control ancillary variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_name is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name = 'warn_max'
        else:
            attr_name = 'fail_max'
    else:
        attr_name = limit_attr_name

    if test_meaning is None:
        test_meaning = ('Data value greater than '
                        'or equal to {}.').format(attr_name)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = np.ma.masked_greater_equal(self._obj[var_name].values,
                                      limit_value)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)
    # Ensure max value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value = float(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value = int(limit_value)

    self._obj[qc_var_name].attrs[attr_name] = limit_value

    return result


def add_equal_to_test(self, var_name, limit_value, test_meaning=None,
                      test_assessment='Bad', test_number=None,
                      flag_value=False, limit_attr_name=None,
                      prepend_text=None):
    '''
        Method to perform an equal test and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value : int or float
            Limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_name : str
            Optional attribute name to store the limit_value under
            quality control ancillary variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_name is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name = 'warn_equal_to'
        else:
            attr_name = 'fail_equal_to'
    else:
        attr_name = limit_attr_name

    if test_meaning is None:
        test_meaning = 'Data value equal to {}.'.format(attr_name)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = np.ma.masked_equal(self._obj[var_name].values, limit_value)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)
    # Ensure max value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value = float(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value = int(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (str(0), np.str_, np.string_):
        limit_value = str(limit_value)

    self._obj[qc_var_name].attrs[attr_name] = limit_value

    return result


def add_not_equal_to_test(self, var_name, limit_value, test_meaning=None,
                          test_assessment='Bad', test_number=None,
                          flag_value=False, limit_attr_name=None,
                          prepend_text=None):
    '''
        Method to perform a not equal to test and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value : int or float
            Limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_name : str
            Optional attribute name to store the limit_value under
            quality control ancillary variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_name is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name = 'warn_not_equal_to'
        else:
            attr_name = 'fail_not_equal_to'
    else:
        attr_name = limit_attr_name

    if test_meaning is None:
        test_meaning = 'Data value not equal to {}.'.format(attr_name)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = np.ma.masked_not_equal(self._obj[var_name].values, limit_value)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)

    # Ensure max value attribute is matching data type
    if self._obj[var_name].values.dtype in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value = float(limit_value)
    elif self._obj[var_name].values.dtype in \
            (int(0), np.int16, np.int32, np.int64):
        limit_value = int(limit_value)
    elif self._obj[var_name].values.dtype.type in \
            (str(0), np.str_, np.string_):
        limit_value = str(limit_value)

    self._obj[qc_var_name].attrs[attr_name] = limit_value

    return result


def add_outside_test(self, var_name, limit_value_lower, limit_value_upper,
                     test_meaning=None,
                     test_assessment='Bad', test_number=None,
                     flag_value=False, limit_attr_names=None,
                     prepend_text=None):
    '''
        Method to perform a less than or greater than test
        (i.e. outide minumum and maximum value) and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value_lower : int or float
            Lower limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        limit_value_upper : int or float
            Uppler limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_names : list of str
            Optional attribute name to store the limit_value under
            quality control ancillary variable. First value is
            lower limit attribute name and second value is
            upper limit attribute name.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.


    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_names is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name_lower = 'warn_lower_range'
            attr_name_upper = 'warn_upper_range'
        else:
            attr_name_lower = 'fail_lower_range'
            attr_name_upper = 'fail_upper_range'
    else:
        attr_name_lower = limit_attr_names[0]
        attr_name_upper = limit_attr_names[1]

    if test_meaning is None:
        test_meaning = ('Data value less than {} '
                        'or greater than {}.').format(attr_name_lower,
                                                      attr_name_upper)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    with np.errstate(invalid='ignore'):
        data = np.ma.masked_outside(self._obj[var_name].values,
                                    limit_value_lower, limit_value_upper)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)
    # Ensure limit value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value_lower = float(limit_value_lower)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value_lower = int(limit_value_lower)

    # Ensure limit value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value_upper = float(limit_value_upper)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value_upper = int(limit_value_upper)

    self._obj[qc_var_name].attrs[attr_name_lower] = limit_value_lower

    self._obj[qc_var_name].attrs[attr_name_upper] = limit_value_upper

    return result


def add_inside_test(self, var_name, limit_value_lower, limit_value_upper,
                    test_meaning=None, test_assessment='Bad',
                    test_number=None, flag_value=False,
                    limit_attr_names=None,
                    prepend_text=None):
    '''
        Method to perform a greater than or less than test
        (i.e. between minumum and maximum value) and add
        result to ancillary quality control varaible. If ancillary
        quality control variable does not exist it will be created.

        Parameters
        ----------
        var_name : str
            Data variable name.
        limit_value_lower : int or float
            Lower limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        limit_value_upper : int or float
            Uppler limit value to use in test. The value will be written
            to the quality control variable as an attribute.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        limit_attr_names : list of str
            Optional attribute name to store the limit_value under
            quality control ancillary variable. First value is
            lower limit attribute name and second value is
            upper limit attribute name.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.


    '''

    qc_var_name = self._obj.qcfilter.check_for_ancillary_qc(var_name)

    if limit_attr_names is None:
        if test_assessment == 'Suspect' or test_assessment == 'Indeterminate':
            attr_name_lower = 'warn_lower_range_inner'
            attr_name_upper = 'warn_upper_range_inner'
        else:
            attr_name_lower = 'fail_lower_range_inner'
            attr_name_upper = 'fail_upper_range_inner'
    else:
        attr_name_lower = limit_attr_names[0]
        attr_name_upper = limit_attr_names[1]

    if test_meaning is None:
        test_meaning = ('Data value greater than {} '
                        'or less than {}.').format(attr_name_lower,
                                                   attr_name_upper)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    with np.errstate(invalid='ignore'):
        data = np.ma.masked_inside(self._obj[var_name].values,
                                   limit_value_lower, limit_value_upper)
    if data.mask.size == 1:
        data.mask = np.full(data.data.shape, data.mask, dtype=bool)
    index = np.where(data.mask)[0]

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)

    # Ensure limit value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value_lower = float(limit_value_lower)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value_lower = int(limit_value_lower)

    # Ensure limit value attribute is matching data type
    if self._obj[var_name].values.dtype.type in \
            (type(0.0), np.float16, np.float32, np.float64):
        limit_value_upper = float(limit_value_upper)
    elif self._obj[var_name].values.dtype.type in \
            (int(0), np.int8, np.int16, np.int32, np.int64):
        limit_value_upper = int(limit_value_upper)

    self._obj[qc_var_name].attrs[attr_name_lower] = limit_value_lower

    self._obj[qc_var_name].attrs[attr_name_upper] = limit_value_upper

    return result


def add_persistence_test(self, var_name, window=10, test_limit=0.0001,
                         test_meaning=None, test_assessment='Bad',
                         test_number=None, flag_value=False,
                         prepend_text=None):
    '''
        Method to perform a persistence test over 1-D data..

        Parameters
        ----------
        var_name : str
            Data variable name.
        window : int
            Optional number of data samples to use in the calculation of
            standard deviation to test for consistent data.
        test_limit : float
            Optional test limit to use where the standard deviation less
            than will trigger the test.
        test_meaning : str
            The optional text description to add to flag_meanings
            describing the test. Will add a default if not set.
        test_assessment : str
            Optional single word describing the assessment of the test.
            Will set a default if not set.
        test_number : int
            Optional test number to use. If not set will ues next
            avaialble test number.
        flag_value : boolean
            Indicates that the tests are stored as integers
            not bit packed values in quality control variable.
        prepend_text : str
            Optional text to prepend to the test meaning.
            Example is indicate what institution added the test.

    '''

    if test_meaning is None:
        test_meaning = ('Data failing persistence test. '
                        'Standard Deviation over a window of {} values '
                        'less than {}.').format(window, test_limit)

    if prepend_text is not None:
        test_meaning = ': '.join((prepend_text, test_meaning))

    data = self._obj[var_name].values

    stddev = np.nanstd(rolling_window(data, window), axis=-1)

    with np.errstate(invalid='ignore'):
        index = np.where(stddev < test_limit)

    result = self._obj.qcfilter.add_test(
        var_name, index=index,
        test_number=test_number,
        test_meaning=test_meaning,
        test_assessment=test_assessment,
        flag_value=flag_value)

    return result
