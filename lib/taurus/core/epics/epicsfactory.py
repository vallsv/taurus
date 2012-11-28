#!/usr/bin/env python
#############################################################################
##
## This file is part of Taurus, a Tango User Interface Library
## 
## http://www.tango-controls.org/static/taurus/latest/doc/html/index.html
##
## Copyright 2011 CELLS / ALBA Synchrotron, Bellaterra, Spain
## 
## Taurus is free software: you can redistribute it and/or modify
## it under the terms of the GNU Lesser General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## Taurus is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Lesser General Public License for more details.
## 
## You should have received a copy of the GNU Lesser General Public License
## along with Taurus.  If not, see <http://www.gnu.org/licenses/>.
##
#############################################################################

'''
Epics module. See __init__.py for more detailed documentation
'''
__all__ = ['EpicsFactory', 'EpicsDatabase', 'EpicsDevice', 
           'EpicsAttribute','EpicsConfiguration', 
           'EpicsConfigurationNameValidator', 'EpicsDeviceNameValidator', 
           'EpicsAttributeNameValidator']



import time, re, weakref
import taurus.core
from taurus.core.taurusexception import TaurusException
import taurus.core.util
from taurus.core import MatchLevel, TaurusSWDevState, SubscriptionState, TaurusEventType
#import epics

class AbstractEpicsNameValidator(taurus.core.util.Singleton):
    #The groups in a match object using the regexp below are:
    #    1: scheme; named as 'scheme'
    #    2: EPICS PV name (in the case of attribute names) or same as $3 (in the case of device names) 
    #    3: device name including the trailing base_sep; optional
    #    4: device name; optional; named as 'devname'
    #    5: base separator if it appears on the URI; named as 'base_sep'
    #    6: attribute name;optional; named as 'attrname'
    #
    #    Reconstructing the names
    #    attrname= $6
    #    devname= $4 or EpicsFactory.DEFAULT_DEVICE
    #    fullname= "epics://%s"%($2)
    # 
    base_sep = ':'
    #                1                   2             34               5                 6
    name_pattern = '^(?P<scheme>epics)://(?P<epicsname>((?P<devname>[^?#]+)(?P<base_sep>%s))?(?P<attrname>[^?#%s]+)?)'%(base_sep, base_sep)
    
    def __init__(self):
        """ Initialization. Nothing to be done here for now."""
        pass
    
    def init(self, *args, **kwargs):
        """Singleton instance initialization."""
        self.name_re = re.compile(self.name_pattern)
        
    def isValid(self,s, matchLevel = MatchLevel.ANY):
        return self.name_re.match(s) is not None
        
    def getParams(self, s):
        m = self.attrname_re.match(s)
        if m is None:
            return None
        return m.groupdict()

    def getNames(self, s, factory=None):
        """Returns the full, normal and simple names for this object, or None if there is no match'''
        """
        raise RuntimeError('Not Allowed to call this method from subclasses')
    
    def getDeviceName(self, s, full=True):
        '''
        returns the device name for the given attribute name. 
        The "full" argument is ignored since the DB is never included in the epics models
        '''
        m = self.name_re.match(s)
        if m is None:
            return None
        devname = m.group('devname') or EpicsFactory.DEFAULT_DEVICE
        return 'epics://%s%s'%(devname,m.group('base_sep'))
    
    def getDBName(self, s):
        '''returns the full data base name for the given attribute name.
        Note: the DB name is not a valid epics URI because the epics scheme does not implement a DB model'''
        dbname = EpicsFactory.DEFAULT_DATABASE
        return dbname
    

class EpicsAttributeNameValidator(AbstractEpicsNameValidator):
    
    def isValid(self,s, matchLevel = MatchLevel.ANY):
        m = self.name_re.match(s)
        return m is not None and m.group('attrname') #the model contains an attrname 
    
    def getNames(self, s, factory=None):
        """Returns the complete, normal and short names.
        
        For example::
        
            >>> EpicsDeviceNameValidator.getNames("epics://foo:bar:baz")
            >>> ("epics://foo:bar:baz", "foo:bar:baz", "baz")
        
        """
        m = self.name_re.match(s)
        if m is None:
            return None
        #The following comments are for an example name like: "epics://foo:bar:baz"
        attr_name = m.group('attrname') # attr_name = "baz"
        normal_name = m.group('epicsname')  #normal_name = "foo:bar:baz"
        fullname = "%s://%s"%(m.group('scheme'),normal_name) #fullname = "epics://foo:bar:baz"
        return fullname, normal_name, attr_name
        

class EpicsDeviceNameValidator(AbstractEpicsNameValidator):
    '''A validator of names for :class:`EpicsDevice`. By taurusconvention, 
    the model name for an epics device name *must* end with the base separator
    (in order to distinguish device names from attribute names)'''
    
    def isValid(self,s, matchLevel = MatchLevel.ANY):
        m = self.name_re.match(s)
        return m is not None and not m.group('attrname') #to be a device it must not contain an attribute
    
    def getNames(self, s, factory=None):
        """Returns the complete, normal and short names. (note: complete=normal)
        
        :param s: (str) input string describing the device
        :param factory: (TaurusFactory) [Unused]
        
        :return: (tuple<str,str,str> or None) A tuple of complete, normal and
                 short names, or None if s is an invalid device name
        """
        m = self.name_re.match(s)
        if m is None:
            return None
        #The following comments are for a name of the type: "epics://foo:bar:" 
        devname = m.group('devname')  # foo:bar
        normal_name = m.group('epicsname') #foo:bar:
        full_name = self.getDeviceName(s, full=True) #epics://foo:bar:
        return full_name, normal_name, devname


class EpicsConfigurationNameValidator(AbstractEpicsNameValidator):
    pass #@todo
#    '''A validator of names for :class:`EpicsConfiguration`'''
#    # The groups in a match object using the regexp below are:
#    #    1: scheme; named as 'scheme'
#    #    2: 
#    #    3: database name; optional; named as 'dbname'
#    #    4: 
#    #    5: device name; optional; named as 'devname'
#    #    6: transformationstring; named as 'attrname'
#    #    7:
#    #    8: substitution symbols (semicolon separated key=val pairs) ; optional; named as 'subst'
#    #    9:
#    #    A: configuration key; named as 'cfgkey'
#    #
#    #    Reconstructing the names
#    #                 1                             2   3                     4    5                      6                    7                    8                  9                 A                    
#    name_pattern = r'^(?P<scheme>epics)://(db=(?P<dbname>[^?#;]+);)?(dev=(?P<devname>[^?#;]+);)?(?P<attrname>[^?#;]+)(\?(?!configuration=)(?P<subst>[^#?]*))?(\?configuration=?(?P<cfgkey>[^#?]*))$'
#        
#    def isValid(self,s, matchLevel = MatchLevel.ANY):
#        m = self.name_re.match(s)
#        if m is None: 
#            return False
#        elif matchLevel == MatchLevel.COMPLETE:
#            return m.group('devname') is not None and m.group('dbname') is not None
#        else:
#            return True
#
#    def getNames(self, s, factory=None):
#        """Returns the complete, normal and short names"""
#        m = self.name_re.match(s)
#        if m is None:
#            return None
#        #The following comments are for an example name like: "eval://dev=foo;bar*blah?bar=123;blah={a/b/c/d}?configuration=label"
#        cfg_key = m.group('cfgkey') # cfg_key = "label"
#        attr_name = m.group('attrname')
#        normal_name = "%s;%s?configuration"%(self.getDeviceName(s, full=False),attr_name) #normal_name = "eval://dev=foo;bar*blah?configuration"
#        expanded_attr_name = self.getExpandedTransformation(s)
#        fullname = "%s;%s?configuration"%(self.getDeviceName(s, full=True),expanded_attr_name) #fullname = "eval://db=_DefaultEvalDB;dev=foo;123*{a/b/c/d}?configuration"
#        return fullname, normal_name, cfg_key
#    
#    def getAttrName(self, s):
#        names = self.getNames(s)
#        if names is None: return None
#        return names[0][:-len('?configuration')] #remove the "?configuration" substring from the fullname
#        

class EpicsDatabase(taurus.core.TaurusDatabase):
    '''
    Dummy database class for Epics (the Database concept is not used in the Epics scheme)
    
    .. warning:: In most cases this class should not be instantiated directly.
                 Instead it should be done via the :meth:`EpicsFactory.getDataBase`
    '''
    def factory(self):
        return EpicsFactory()
        
    def __getattr__(self, name):
        return "EpicsDatabase object calling %s" % name


class EpicsDevice(taurus.core.TaurusDevice):
    '''
    An Epics device object. 
    @todo: For the moment is a dummy object. Eventually we may map it to an epics record.
    
    .. seealso:: :mod:`taurus.core.epics`
    
    .. warning:: In most cases this class should not be instantiated directly.
                 Instead it should be done via the :meth:`EpicsFactory.getDevice`
    '''
    
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    # TaurusModel necessary overwrite
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    # helper class property that stores a reference to the corresponding factory
    _factory = None
    
    @classmethod
    def factory(cls):
        if cls._factory is None:
            cls._factory = taurus.Factory(scheme='epics')
        return cls._factory
    
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    # TaurusDevice necessary overwrite
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    def _createHWObject(self):
        return 'Epics'
    
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    def getAttribute(self, attrname):
        """Returns the attribute object given its name"""
        full_attrname = "%s%s"%(self.getFullName(), attrname)
        return self.factory().getAttribute(full_attrname)
    
    @classmethod
    def getNameValidator(cls):
        return EpicsDeviceNameValidator()
    
    def decode(self, event_value):
        if isinstance(event_value, int): # TaurusSWDevState
            new_sw_state = event_value
        else:
            self.info("Unexpected value to decode: %s" % str(event_value))
            new_sw_state = TaurusSWDevState.Crash
        value = taurus.core.TaurusAttrValue() 
        value.value = new_sw_state
        return value
    

class EpicsAttribute(taurus.core.TaurusAttribute):
    '''
    A :class:`TaurusAttribute` that gives access to an Epics Process Variable.
    
    .. seealso:: :mod:`taurus.core.epics` 
    
    .. warning:: In most cases this class should not be instantiated directly.
                 Instead it should be done via the :meth:`EpicsFactory.getAttribute`
    '''
    
    def __init__(self, name, parent, storeCallback = None):
        self.call__init__(taurus.core.TaurusAttribute, name, parent, storeCallback=storeCallback)
        
        self._value = taurus.core.TaurusAttrValue()
        self._value.config.writable = False #@todo: this can be checked  with ca_info(pvname, Channel(pvname)).writable
        self._validator= self.getNameValidator()
        # reference to the configuration object
        self.__attr_config = None#taurus.core.TaurusConfiguration()
        self.__subscription_state = SubscriptionState.Unsubscribed
        #self.__pv = epics.PV('self.getNormalName()')

    def __getattr__(self,name):
        return getattr(self._getRealConfig(), name)
    
    def _getRealConfig(self):
        """ Returns the current configuration of the attribute."""
        if self.__attr_config is None:
            cfg_name = "%s?configuration" % self.getFullName()
            self.__attr_config = EpicsConfiguration(cfg_name, self)
        return self.__attr_config
            
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    # Necessary to overwrite from TaurusAttribute
    #-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-~-
    def isNumeric(self):
        return True
        
    def isBoolean(self):
        return isinstance(self._value.value, bool)
    
    def isState(self):
        return False

    def getDisplayValue(self,cache=True):
        return str(self.read(cache=cache).value)

    def encode(self, value):
        return value

    def decode(self, attr_value):
        return attr_value

    def write(self, value, with_read=True):
        raise TaurusException('Epics writeable attributes not supported yet') #@todo: support writable attributes

    def read(self, cache=True):
        '''returns the value of the attribute.
        
        :param cache: (bool) If True (default), the last calculated value will
                      be returned. If False, the referenced values will be re-
                      read and the transformation string will be re-evaluated
                      
        :return: attribute value
        '''
        if not cache:
            pass #@todo force a reading with caget
            #v = self.__pv.get()
        return self._value    

    def poll(self):
        v = self.read(cache=False)
        self.fireEvent(TaurusEventType.Periodic, v)
            
    def _subscribeEvents(self): 
        pass #@todo
        
    def _unsubscribeEvents(self):
        pass #@todo

    def isUsingEvents(self):
        return False #@todo
        
#------------------------------------------------------------------------------ 

    def factory(self):
        return EpicsFactory()
    
    @classmethod
    def getNameValidator(cls):
        return EpicsAttributeNameValidator()

    def __fireRegisterEvent(self, listener):
        #fire a first change event
        try:
            v = self.read()
            self.fireEvent(TaurusEventType.Change, v, listener)
        except:
            self.fireEvent(TaurusEventType.Error, None, listener)
    
    def addListener(self, listener):
        """ Add a TaurusListener object in the listeners list.
            If it is the first listener, it triggers the subscription to the referenced attributes.
            If the listener is already registered nothing happens."""
        
        #subscribe to configuration events for this attribute
        cfg = self.getConfig()
        cfg.addListener(listener)
        
        initial_subscription_state = self.__subscription_state
        
        ret = taurus.core.TaurusAttribute.addListener(self, listener)

        if not ret:
            return ret
        
        if self.__subscription_state == SubscriptionState.Unsubscribed:
            for refobj in self._references:
                refobj.addListener(self) #subscribe to the referenced attributes
            self.__subscription_state = SubscriptionState.Subscribed

        assert len(self._listeners) >= 1        
        #if initial_subscription_state == SubscriptionState.Subscribed:
        if len(self._listeners) > 1 and (initial_subscription_state == SubscriptionState.Subscribed or self.isPollingActive()):
            taurus.Manager().addJob(self.__fireRegisterEvent, None, (listener,))
        return ret
        
    def removeListener(self, listener):
        """ Remove a TaurusListener from the listeners list. If polling enabled 
            and it is the last element then stop the polling timer.
            If the listener is not registered nothing happens."""
        ret = taurus.core.TaurusAttribute.removeListener(self, listener)

        cfg = self._getRealConfig()
        cfg.removeListener(listener)
        
        if ret and not self.hasListeners():
            self._deactivatePolling()
            self.__subscription_state = SubscriptionState.Unsubscribed
        return ret
    

class EpicsConfiguration(taurus.core.TaurusConfiguration):
    '''
    A :class:`TaurusConfiguration` 
    
    .. seealso:: :mod:`taurus.core.epics` 
    
    .. warning:: In most cases this class should not be instantiated directly.
                 Instead it should be done via the :meth:`EpicsFactory.getConfig`
    '''
    def __init__(self, name, parent, storeCallback = None):
        self.call__init__(taurus.core.TaurusConfiguration, name, parent, storeCallback=storeCallback)
        
        #fill the attr info
        i = parent.read().config
        a=parent
        d=self._getDev()
        # add dev_name, dev_alias, attr_name, attr_full_name
        i.dev_name = d.getNormalName()
        i.dev_alias = d.getSimpleName()
        i.attr_name = a.getSimpleName()
        i.attr_fullname = a.getNormalName()
        i.label = a.getSimpleName()
        self._attr_info = i
        
    def __getattr__(self, name): 
        try:
            return getattr(self._attr_info,name)
        except:
            raise AttributeError("'%s'object has no attribute '%s'"%(self.__class__.__name__, name))
    @classmethod
    def getNameValidator(cls):
        return EpicsConfigurationNameValidator()
        
    def _subscribeEvents(self): 
        pass
    
    def _unSubscribeEvents(self):
        pass   
    
    def factory(self):
        EpicsFactory()
    
    def getValueObj(self, cache=True):
        """ Returns the current configuration for the attribute."""
        return self._attr_info   
    
class EpicsFactory(taurus.core.util.Singleton, taurus.core.TaurusFactory, taurus.core.util.Logger):
    """
    A Singleton class that provides Epics related objects.
    """

    schemes = ("epics",)
    DEFAULT_DEVICE = '_DefaultEpicsDevice'
    DEFAULT_DATABASE = '_DefaultEpicslDB'
    def __init__(self):
        """ Initialization. Nothing to be done here for now."""
        pass

    def init(self, *args, **kwargs):
        """Singleton instance initialization."""
        name = self.__class__.__name__
        self.call__init__(taurus.core.util.Logger, name)
        self.call__init__(taurus.core.TaurusFactory)
        self.epics_attrs = weakref.WeakValueDictionary()
        self.epics_devs = weakref.WeakValueDictionary()
        self.epics_configs = weakref.WeakValueDictionary()
        
    def findObjectClass(self, absolute_name):
        """
        Obtain the class object corresponding to the given name.
        """
        if EpicsConfiguration.isValid(absolute_name):
            return EpicsConfiguration
        elif EpicsDevice.isValid(absolute_name):
            return EpicsDevice
        elif EpicsAttribute.isValid(absolute_name):
            return EpicsAttribute
        else:
            self.debug("Not able to find Object class for %s" % absolute_name)
            self.traceback()
            return None

    def getDatabase(self, db_name=None):
        """Obtain the EpicsDatabase object.
        
        :param db_name: (str) this is ignored because only one dummy database is supported
                           
        :return: (EpicsDatabase)
        """
        if not hasattr(self, "_db"):
            self._db = EpicsDatabase(self.DEFAULT_DATABASE)
        return self._db

    def getDevice(self, dev_name):
        """Obtain the EpicsDevice object.
        
        :param dev_name: (str) this is ignored because only one dummy device is supported
                           
        :return: (EpicsDevice)
        
        .. todo:: Epics records may be implemented as taurus devices...
        """
        d = self.epics_devs.get(dev_name, None) #first try with the given name
        if d is None: #if not, try with the full name
            validator = EpicsDevice.getNameValidator()
            names = validator.getNames(dev_name)
            if names is None:
                raise TaurusException("Invalid epics device name %s" % dev_name)
            fullname = names[0]
            d = self.epics_devs.get(fullname, None)
            if d is None: #if the full name is not there, create one
                db = self.getDatabase()
                d = EpicsDevice(fullname, parent=db, storeCallback=self._storeDev) #use full name
        return d
    
    def getAttribute(self, attr_name):
        """Obtain the object corresponding to the given attribute name. If the 
        corresponding attribute already exists, the existing instance is
        returned. Otherwise a new instance is stored and returned. The 
        device associated to this attribute will also be created if necessary.
           
        :param attr_name: (str) the attribute name string. See
                          :mod:`taurus.core.epics` for valid attribute names
        
        :return: (EpicsAttribute)
         
        @throws TaurusException if the given name is invalid.
        """
        a = self.epics_attrs.get(attr_name, None) #first try with the given name
        if a is None: #if not, try with the full name
            validator = EpicsAttribute.getNameValidator()
            names = validator.getNames(attr_name)
            if names is None:
                raise TaurusException("Invalid evaluation attribute name %s" % attr_name)
            fullname = names[0]
            a = self.epics_attrs.get(fullname, None)
            if a is None: #if the full name is not there, create one
                dev = self.getDevice(validator.getDeviceName(attr_name))
                a = EpicsAttribute(fullname, parent=dev, storeCallback=self._storeAttr) #use full name
        return a

    def getConfiguration(self, param):
        """getConfiguration(param) -> taurus.core.TaurusConfiguration

        Obtain the object corresponding to the given attribute or full name.
        If the corresponding configuration already exists, the existing instance
        is returned. Otherwise a new instance is stored and returned.

        @param[in] param taurus.core.TaurusAttribute object or full configuration name
           
        @return a taurus.core.TaurusAttribute object
        @throws TaurusException if the given name is invalid.
        """
        if isinstance(param, str):
            return self._getConfigurationFromName(param)
        return self._getConfigurationFromAttribute(param)

    def _getConfigurationFromName(self, cfg_name):
        cfg = self.epics_configs.get(cfg_name, None) #first try with the given name
        if cfg is None: #if not, try with the full name
            validator = EpicsConfiguration.getNameValidator()
            names = validator.getNames(cfg_name)
            if names is None:
                raise TaurusException("Invalid evaluation configuration name %s" % cfg_name)
            fullname = names[0]
            cfg = self.epics_configs.get(fullname, None)
            if cfg is None: #if the full name is not there, create one
                attr = self.getAttribute(validator.getAttrName(cfg_name))
                cfg = EpicsConfiguration(names[0], parent=attr, storeCallback=self._storeConfig) #use full name
        return cfg
        
    def _getConfigurationFromAttribute(self, attr):
        cfg = attr.getConfig()
        cfg_name = attr.getFullName() + "?configuration"
        self.epics_configs[cfg_name] = cfg
        return cfg
    
    def _storeDev(self, dev):
        name = dev.getFullName()
        exists = self.epics_devs.get(name)
        if exists is not None:
            if exists == dev: 
                self.debug("%s has already been registered before" % name)
                raise taurus.core.DoubleRegistration
            else:
                self.debug("%s has already been registered before with a different object!" % name)
                raise taurus.core.DoubleRegistration
        self.epics_devs[name] = dev
    
    def _storeAttr(self, attr):
        name = attr.getFullName()
        exists = self.epics_attrs.get(name)
        if exists is not None:
            if exists == attr: 
                self.debug("%s has already been registered before" % name)
                raise taurus.core.DoubleRegistration
            else:
                self.debug("%s has already been registered before with a different object!" % name)
                raise taurus.core.DoubleRegistration
        self.epics_attrs[name] = attr
        
    def _storeConfig(self, fullname, config):
        #name = config.getFullName()
        name = fullname
        exists = self.epics_configs.get(name)
        if exists is not None:
            if exists == config: 
                self.debug("%s has already been registered before" % name)
                raise taurus.core.DoubleRegistration
            else:
                self.debug("%s has already been registered before with a different object!" % name)
                raise taurus.core.DoubleRegistration
        self.epics_configs[name] = config
        
    def addAttributeToPolling(self, attribute, period, unsubscribe_evts = False):
        """Activates the polling (client side) for the given attribute with the
           given period (seconds).

           :param attribute: (taurus.core.tango.TangoAttribute) attribute name.
           :param period: (float) polling period (in seconds)
           :param unsubscribe_evts: (bool) whether or not to unsubscribe from events
        """
        tmr = self.polling_timers.get(period,taurus.core.TaurusPollingTimer(period))
        self.polling_timers[period] = tmr
        tmr.addAttribute(attribute, self.isPollingEnabled())
        
    def removeAttributeFromPolling(self, attribute):
        """Deactivate the polling (client side) for the given attribute. If the
           polling of the attribute was not previously enabled, nothing happens.

           :param attribute: (str) attribute name.
        """
        p = None
        for period,timer in self.polling_timers.iteritems():
            if timer.containsAttribute(attribute):
                timer.removeAttribute(attribute)
                if timer.getAttributeCount() == 0:
                    p = period
                break
        if p:
            del self.polling_timers[period]
            

    

#===============================================================================
# Just for testing
#===============================================================================
def test1():
    f = EpicsFactory()
    d = f.getDevice('epics://foo:bar:')
    a = f.getAttribute('epics://foo:bar:baz')
#    c = f.getConfiguration('eval://2*{sys/tg_test/1/short_scalar}?configuration=label')
#    cp = a.getConfig()
    print "FACTORY:", f
    print "DEVICE:", d, d.getSimpleName(), d.getNormalName(), d.getFullName()
    print "ATTRIBUTE", a, a.getSimpleName(), a.getNormalName(), a.getFullName()
#    print "CONFIGURATION", c, c.getSimpleName()
#    print "CONFIGPROXY", cp, cp.getSimpleName()
#    print
#    print c.getValueObj()
#    print c.getUnit()
    

def test2():
    a=taurus.Attribute('eval://[{sys/tg_test/1/short_scalar},{sys/tg_test/1/double_scalar}, {sys/tg_test/1/short_scalar}+{sys/tg_test/1/double_scalar}]')
    #a=taurus.Attribute('eval://2*{sys/tg_test/1/short_scalar}+rand()')  
    class Dummy:
        n=0
        def eventReceived(self, s,t,v):
            print self.n, v
            self.n += 1
    kk = Dummy()
    a.addListener(kk)
    while kk.n <= 2:
        time.sleep(1)
    a.removeListener(kk)
#    while kk.n <= 20:
#        time.sleep(1)        
    
def test3():
    import sys
    from taurus.qt.qtgui.application import TaurusApplication
    from taurus.qt.qtgui.panel import TaurusForm
#    from taurus.qt.qtgui.plot import TaurusTrend
#    from taurus.qt.qtgui.display import TaurusLabel
    app = TaurusApplication()
    
    w = TaurusForm()
#    w=TaurusTrend()
#    w=TaurusLabel()

    w.setModel(['eval://2*short_scalar?short_scalar={sys/tg_test/1/short_scalar}',
                'sys/tg_test/1/short_scalar', 'eval://a<100?a={sys/tg_test/1/short_scalar}', 
                'eval://10*rand()', 'eval://dev=taurus.core.epics.dev_example.FreeSpaceDevice;getFreeSpace("/")/1024/1024'])
#    w.setModel(['eval://2*short_scalar?short_scalar={sys/tg_test/1/short_scalar}'])
#    w.setModel(['sys/tg_test/1/short_scalar'])
#    w.setModel('eval://2*{sys/tg_test/1/short_scalar}?configuration=label')
#    w.setModel('eval://2*{sys/tg_test/1/short_scalar}')
#    w.setModel('sys/tg_test/1/short_scalar?configuration=label')
#    w.setModel('sys/tg_test/1/short_scalar')

#    a=w.getModelObj()
#    print a, a.read().value
    
#    a=w.getModelObj()
#    a.setUnit('asd')
#    c=a.getConfig()

    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    test1()
    
        
