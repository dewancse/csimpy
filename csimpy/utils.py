import os
from tempfile import mkstemp
import sys
import importlib

import libsedml
import libcellml


def get_xpath_namespaces(sed_element):
    """
    Get all the XML namespaces for the given SED-ML element. See https://github.com/fbergmann/libSEDML/issues/77 for
    some background. This will collect all namespaces from the current element and all its parents.

    :param sed_element: the SED-ML element to define the context for fetching namespaces.
    :return: a dictionary of defined namespaces.
    """
    ns = {}
    current_sed_base = sed_element
    while current_sed_base:
        xmlns = current_sed_base.getElementNamespaces()
        if xmlns:
            for n in range(0, xmlns.getNumNamespaces()):
                prefix = xmlns.getPrefix(n)
                if prefix == '':
                    # we can't use a default namespace in XPath so filter it out...
                    continue
                elif prefix in ns:
                    # existing namespace prefixes should not be changed
                    continue
                else:
                    uri = xmlns.getURI(n)
                    ns[prefix] = uri
        current_sed_base = current_sed_base.getParentSedObject()
    return ns


def module_from_string(python_code_string):
    """
    Take the Python code generated by libCellML and load it into a module that can be executed.

    :param module_name: The name to give the generated module.
    :param python_code_string: The string of the Python code.
    :return: The executable module.
    """

    # write the generated code to a temporary file
    fid, filename = mkstemp(suffix='.py', prefix="csimpy_", text=True)
    file = os.fdopen(fid, "w")
    file.write(python_code_string)
    print("Generated code is in: " + filename)
    file.close()
    # and load it back in
    module_name = os.path.splitext(os.path.basename(filename))[0]
    spec = importlib.util.spec_from_file_location(module_name, filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # and delete temporary file
    print("Generated code file: {}; has been deleted.".format(filename))
    os.remove(filename)
    return module


def _get_variable_index(info, component_name, variable_name):
    for i in range(len(info)):
        v = info[i]
        if v['name'] == variable_name and v['component'] == component_name:
            return i
    return -1


def get_array_index_for_variable(module, component_name, variable_name):
    """
    Find the corresponding array and index for the given variable in the generated code module.

    :param module: The instantiated generated code module.
    :param component_name: The name of the component in which the variable exists.
    :param variable_name: The name of the variable to look for.
    :return: The index and array for the variable, array = 1 (VOI), 2 (state), 3 (variable), -1 (unknown)
    """
    i = _get_variable_index([module.VOI_INFO], component_name, variable_name)
    if i >= 0:
        return i, 1
    i = _get_variable_index(module.STATE_INFO, component_name, variable_name)
    if i >= 0:
        return i, 2
    i = _get_variable_index(module.VARIABLE_INFO, component_name, variable_name)
    if i >= 0:
        return i, 3
    return 0, -1


def get_array_index_for_equivalent_variable(module, variable):
    for i in range(variable.equivalentVariableCount()):
        eqv = variable.equivalentVariable(i)
        vname = eqv.name()
        cname = eqv.parent().name()
        print("Checking equivalent variable: {} / {}".format(cname, vname))
        index, array = get_array_index_for_variable(module, cname, vname)
        if array > 0:
            return index, array

    return -1, -1