#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2014-     Thomas Ernst                       offline@gmx.net
#########################################################################
#  Finite state machine plugin for SmartHomeNG
#
#  This plugin is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This plugin is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this plugin. If not, see <http://www.gnu.org/licenses/>.
#########################################################################
from . import StateEngineCondition
from . import StateEngineTools
import collections.abc
from collections import OrderedDict


# Class representing a set of conditions
class SeConditionSet(StateEngineTools.SeItemChild):
    # Name of condition set
    @property
    def name(self):
        return self.__name

    @property
    def id(self):
        return self.__id

    # List of conditions that are part of this condition set
    @property
    def conditions(self):
        return self.__conditions

    @property
    def evals_items(self):
        return self.__evals_items

    @property
    def dict_conditions(self):
        result = OrderedDict()
        for name in self.__conditions:
            result.update({name: self.__conditions[name].get()})
        return result

    # Initialize the condition set
    # abitem: parent SeItem instance
    # name: Name of condition set
    # conditionid: Condition set item or dict
    def __init__(self, abitem, name, conditionid):
        super().__init__(abitem)
        self.__name = name
        self.__id = conditionid
        self.__conditions = OrderedDict()
        self.__evals_items = {}

    def __repr__(self):
        return "SeConditionSet {}".format(self.__conditions)

    # Update condition set
    # item: item containing settings for condition set
    # grandparent_item: grandparent item of item (containing the definition if items and evals)
    def update(self, item, grandparent_item):
        # Update conditions in condition set
        if isinstance(item, collections.abc.Mapping) or isinstance(grandparent_item, collections.abc.Mapping):
            self._log_error("Condition '{0}' item or parent is a dictionary. Something went wrong!", item)
            return

        if item is not None:
            for attribute in item.conf:
                func, name = StateEngineTools.partition_strip(attribute, "_")
                if name == "":
                    continue
                try:
                    # update this condition
                    if name not in self.__conditions:
                        self.__conditions[name] = StateEngineCondition.SeCondition(self._abitem, name)
                    self.__conditions[name].set(func, item.conf[attribute])
                    self.__conditions.move_to_end(name, last=True)

                except ValueError as ex:
                    raise ValueError("Condition {0} error: {1}".format(name, ex))

        # Update item from grandparent_item
        for attribute in grandparent_item.conf:
            func, name = StateEngineTools.partition_strip(attribute, "_")
            if name == "":
                continue
            # update item/eval in this condition

            if func == "se_item" or func == "se_eval":
                if name not in self.__conditions:
                    self.__conditions[name] = StateEngineCondition.SeCondition(self._abitem, name)
                try:
                    self.__conditions[name].set(func, grandparent_item.conf[attribute])
                except ValueError as ex:
                    text = "Item '{0}', Attribute '{1}' Error: {2}"
                    raise ValueError(text.format(grandparent_item.property.path, attribute, ex))
                self.__evals_items.update({name: self.__conditions[name].get()})

    # Check the condition set, optimize and complete it
    # item_state: item to read from
    def complete(self, item_state):
        conditions_to_remove = []
        # try to complete conditions
        for name in self.conditions:
            try:
                if not self.__conditions[name].complete(item_state):
                    conditions_to_remove.append(name)
                    continue
            except ValueError as ex:
                text = "State '{0}', Condition Set '{1}', Condition '{2}' Error: {3}"
                raise ValueError(text.format(item_state.property.path, self.name, name, ex))

        # Remove incomplete conditions
        for name in conditions_to_remove:
            del self.conditions[name]

    # Write the whole condition set to the logger
    def write_to_logger(self):
        for name in self.__conditions:
            self._log_info("Condition '{0}':", name)
            self._log_increase_indent()
            self.__conditions[name].write_to_logger()
            self._log_decrease_indent()

    def __currentconditionset_set(self, conditionsetid, name):
        self._abitem.set_variable('current.conditionset_id', conditionsetid)
        self._abitem.set_variable('current.conditionset_name', name)

    def __previousconditionset_set(self, conditionsetid, name):
        self._abitem.set_variable('previous.conditionset_id', conditionsetid)
        self._abitem.set_variable('previous.conditionset_name', name)

    # Check all conditions in the condition set. Return
    # returns: True = all conditions in set are matching, False = at least one condition is not matching
    def all_conditions_matching(self):
        try:
            self._log_info("Check condition set '{0}'", self.__name)
            self._log_increase_indent()
            self.__previousconditionset_set(self._abitem.get_variable('current.conditionset_id'), self._abitem.get_variable('current.conditionset_name'))
            self.__currentconditionset_set(self.__id.property.path, self.__name)

            for name in self.__conditions:
                if not self.__conditions[name].check():
                    self.__currentconditionset_set('', '')
                    return False
            #self._abitem.previousconditionset_set(self._abitem.get_variable('previous.conditionset_id'), self._abitem.get_variable('previous.conditionset_name'))
            self._abitem.lastconditionset_set(self.__id.property.path, self.__name)
            return True
        finally:
            self._log_decrease_indent()
