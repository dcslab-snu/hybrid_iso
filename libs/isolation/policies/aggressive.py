# coding: UTF-8

import logging

from .base import IsolationPolicy
from .. import ResourceType
from ..isolators import AffinityIsolator, CacheIsolator, IdleIsolator, MemoryIsolator, SchedIsolator
# from ..isolators import AffinityIsolator, CacheIsolator, IdleIsolator, SchedIsolator
# from ..isolators import IdleIsolator, MemoryIsolator
from ...workload import Workload


class AggressivePolicy(IsolationPolicy):
    def __init__(self, fg_wl: Workload, bg_wl: Workload) -> None:
        super().__init__(fg_wl, bg_wl)

        self._is_mem_isolated = False

    @property
    def new_isolator_needed(self) -> bool:
        return isinstance(self._cur_isolator, IdleIsolator)

    def choose_next_isolator(self) -> bool:
        logger = logging.getLogger(__name__)
        logger.debug('looking for new isolation...')

        # if foreground is web server (CPU critical)

        if len(self._fg_wl.bound_cores) * 2 < self._fg_wl.number_of_threads:
            if AffinityIsolator in self._isolator_map and not self._isolator_map[AffinityIsolator].is_max_level:
                self._cur_isolator = self._isolator_map[AffinityIsolator]
                logger.info(f'Starting {self._cur_isolator.__class__.__name__}...')
                return True

        for resource, diff_value in self.contentious_resources():

            if resource is ResourceType.CACHE:
                isolator = self._isolator_map[CacheIsolator]
            elif resource is ResourceType.MEMORY:
                if self._is_mem_isolated:
                    isolator = self._isolator_map[SchedIsolator]
                    self._is_mem_isolated = False
                else:
                    isolator = self._isolator_map[MemoryIsolator]
                    self._is_mem_isolated = True

            else:
                raise NotImplementedError(f'Unknown ResourceType: {resource}')

            if diff_value < 0 and not isolator.is_max_level or \
                    diff_value > 0 and not isolator.is_min_level:
                self._cur_isolator = isolator
                logger.info(f'Starting {self._cur_isolator.__class__.__name__}...')
                return True

        logger.debug('A new Isolator has not been selected')
        return False
