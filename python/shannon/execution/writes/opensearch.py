import logging
from typing import Dict, Optional, Iterable

from opensearchpy import OpenSearch
from opensearchpy.helpers import parallel_bulk
from ray.data import Datasource, Dataset
from ray.data._internal.delegating_block_builder import DelegatingBlockBuilder
from ray.data._internal.execution.interfaces import TaskContext
from ray.data.block import Block, BlockAccessor
from ray.data.datasource import WriteResult

from shannon.execution.basics import (Node, Write)

log = logging.getLogger(__name__)


class OpenSearchWriter(Write):

    def __init__(self, plan: Node,
                 index_name: str,
                 *,
                 os_client_args: Dict,
                 index_settings: Optional[Dict] = None,
                 number_of_allowed_failures_per_block: int = 100,
                 collect_failures_file_path: str = None,
                 **ray_remote_args):
        super().__init__(plan, **ray_remote_args)
        self.index_name = index_name
        self.index_settings = index_settings
        self.os_client_args = os_client_args
        self.number_of_allowed_failures_per_block = number_of_allowed_failures_per_block
        self.collect_failures_file_path = collect_failures_file_path or "failures.txt"

    def execute(self) -> Dataset:
        dataset = self.child().execute()
        dataset.write_datasource(OSDataSource(),
                                 index_name=self.index_name,
                                 index_settings=self.index_settings,
                                 os_client_args=self.os_client_args,
                                 number_of_allowed_failures_per_block=self.number_of_allowed_failures_per_block,
                                 collect_failures_file_path=self.collect_failures_file_path or "failures.txt")

        return dataset


class OSDataSource(Datasource):

    def write(self,
              blocks: Iterable[Block],
              ctx: TaskContext,
              **write_args,
              ) -> WriteResult:
        builder = DelegatingBlockBuilder()
        for block in blocks:
            builder.add_block(block)
        block = builder.build()

        self.write_block(block, **write_args)

        return "ok"

    @staticmethod
    def write_block(block: Block,
                    *,
                    os_client_args: Dict,
                    index_name: str,
                    collect_failures_file_path: str,
                    number_of_allowed_failures_per_block: int,
                    index_settings: Optional[Dict] = None):

        block = BlockAccessor.for_block(block).to_arrow().to_pylist()
        try:
            client = OpenSearch(**os_client_args)
            if not client.indices.exists(index_name):
                if index_settings is not None:
                    client.indices.create(index_name, **index_settings)
                else:
                    client.indices.create(index_name)

        except Exception as e:
            log.error("Exception occurred while creating an index:", e)
            raise RuntimeError("Exception occurred while creating an index", e)

        def create_actions():
            for i, row in enumerate(block):
                action = {
                    "_index": index_name,
                    "_id": i,
                    "_source": row
                }
                yield action

        failures = []
        for success, info in parallel_bulk(client, create_actions()):
            if not success:
                log.error("A Document failed to upload", info)
                failures.append(info)

                if len(failures) > number_of_allowed_failures_per_block:
                    with open(collect_failures_file_path, "a") as f:
                        for doc in failures:
                            f.write(f"{doc}\n")
                    raise RuntimeError(
                        f"{number_of_allowed_failures_per_block} documents failed to index. "
                        f"Refer to {collect_failures_file_path}.")

        log.info("All the documents have been ingested!")
