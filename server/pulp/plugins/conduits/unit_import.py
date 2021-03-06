"""
Contains the definitions for all classes related to the importer's API for
interacting with the Pulp server when importing units.
"""

from gettext import gettext as _
import logging
import sys

from pulp.plugins.conduits import mixins
from pulp.plugins.conduits.mixins import (
    ImporterConduitException, ImporterScratchPadMixin, RepoScratchPadMixin,
    SearchUnitsMixin, AddUnitMixin)
import pulp.server.managers.factory as manager_factory


_logger = logging.getLogger(__name__)


class ImportUnitConduit(ImporterScratchPadMixin, RepoScratchPadMixin,
                        SearchUnitsMixin, AddUnitMixin):
    """
    Used to interact with the Pulp server while importing units into a
    repository. Instances of this class should *not* be cached between import
    calls. Each call will be issued its own conduit instance that is scoped
    to a single import.

    Instances of this class are thread-safe. The importer implementation is
    allowed to do whatever threading makes sense to optimize the import.
    Calls into this instance do not have to be coordinated for thread safety,
    the instance will take care of it itself.
    """

    def __init__(self, source_repo_id, dest_repo_id, source_importer_id, dest_importer_id):
        """
        :param source_repo_id: ID of the repository from which units are being copied
        :type  source_repo_id: str
        :param dest_repo_id: ID of the repository into which units are being copied
        :type  dest_repo_id: str
        :param source_importer_id: ID of the importer on the source repository
        :type  source_importer_id: str
        :param dest_importer_id:  ID of the importer on the destination repository
        :type  dest_importer_id: str
        """
        ImporterScratchPadMixin.__init__(self, dest_repo_id, dest_importer_id)
        RepoScratchPadMixin.__init__(self, dest_repo_id, ImporterConduitException)
        SearchUnitsMixin.__init__(self, ImporterConduitException)
        AddUnitMixin.__init__(self, dest_repo_id, dest_importer_id)

        self.source_repo_id = source_repo_id
        self.dest_repo_id = dest_repo_id

        self.source_importer_id = source_importer_id
        self.dest_importer_id = dest_importer_id

        self.__association_manager = manager_factory.repo_unit_association_manager()
        self.__association_query_manager = manager_factory.repo_unit_association_query_manager()

    def __str__(self):
        return _('ImportUnitConduit for repository [%(r)s]') % {'r': self.repo_id}

    def associate_unit(self, unit):
        """
        Associates the given unit with the destination repository for the import.

        This call is idempotent. If the association already exists, this call
        will have no effect.

        :param unit: unit object returned from the init_unit call
        :type  unit: pulp.plugins.model.Unit

        :return: object reference to the provided unit
        :rtype:  pulp.plugins.model.Unit
        """

        try:
            self.__association_manager.associate_unit_by_id(
                self.dest_repo_id, unit.type_id, unit.id)
            return unit
        except Exception, e:
            _logger.exception(_('Content unit association failed [%s]' % str(unit)))
            raise ImporterConduitException(e), None, sys.exc_info()[2]

    def get_source_units(self, criteria=None, as_generator=False):
        """
        Returns the collection of content units associated with the source
        repository for a unit import.

        Units returned from this call will have the id field populated and are
        useable in any calls in this conduit that require the id field.

        :param criteria: used to scope the returned results or the data within;
               the Criteria class can be imported from this module
        :type  criteria: L{UnitAssociationCriteria}

        :return: list of unit instances
        :rtype:  list of pulp.plugins.model.AssociatedUnit
        """
        return mixins.do_get_repo_units(self.source_repo_id, criteria, ImporterConduitException,
                                        as_generator=as_generator)

    def get_destination_units(self, criteria=None):
        """
        Returns the collection of content units associated with the destination
        repository for a unit import.

        Units returned from this call will have the id field populated and are
        useable in any calls in this conduit that require the id field.

        :param criteria: used to scope the returned results or the data within;
               the Criteria class can be imported from this module
        :type  criteria: UnitAssociationCriteria

        :return: list of unit instances
        :rtype:  list of pulp.plugins.model.AssociatedUnit
        """
        return mixins.do_get_repo_units(self.dest_repo_id, criteria, ImporterConduitException)
