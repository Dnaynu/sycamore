import ray

from sycamore.data import Document, MetadataDocument
from sycamore.plan_nodes import Node
from sycamore.transforms.similarity import HuggingFaceTransformersSimilarityScorer, ScoreSimilarity


class TestSimilarityScorer:

    def test_transformers_similarity_scorer(self):
        similarity_scorer = HuggingFaceTransformersSimilarityScorer()
        score_property_name = "similarity_score"
        query = "this is a cat"

        dicts = [
            {
                "doc_id": 1,
                "elements": [
                    {"text_representation": "here is an animal with 4 legs and whiskers"},
                ],
            },
            {
                "doc_id": 2,
                "elements": [
                    {"id": 7, "text_representation": "this is a cat"},
                    {"id": 1, "text_representation": "this is a dog"},
                ],
            },
            {
                "doc_id": 3,
                "elements": [
                    {"text_representation": "this is a dog"},
                ],
            },
            {"doc_id": 4, "elements": [{"text_representation": "the number of pages in this document are 253"}]},
            {  # handle empty element
                "doc_id": 5,
                "elements": [
                    {"id": 1},
                ],
            },
        ]
        docs = [Document(item) for item in dicts]
        result = similarity_scorer.generate_similarity_scores(
            docs, query=query, score_property_name=score_property_name
        )
        result.sort(key=lambda doc: doc.properties.get(score_property_name, float("-inf")), reverse=True)
        assert [doc.doc_id for doc in result] == [2, 1, 3, 4, 5]

        assert result[0].properties[score_property_name + "_source_element_id"] == 7

    def test_transformers_similarity_scorer_no_doc_structure(self):
        similarity_scorer = HuggingFaceTransformersSimilarityScorer(ignore_doc_structure=True)
        score_property_name = "similarity_score"
        query = "this is a cat"

        dicts = [
            {"doc_id": 1, "text_representation": "here is an animal with 4 legs and whiskers"},
            {"doc_id": 2, "text_representation": "this is a cat"},
            {"doc_id": 3, "text_representation": "this is a dog"},
            {
                "doc_id": 4,
                "elements": [
                    {"text_representation": "this doc doesn't have a text representation but instead has an element"}
                ],
            },
            {"doc_id": 5, "text_representation": "the number of pages in this document are 253"},
        ]
        docs = [Document(item) for item in dicts]
        result = similarity_scorer.generate_similarity_scores(
            docs, query=query, score_property_name=score_property_name
        )
        result.sort(key=lambda doc: doc.properties.get(score_property_name, float("-inf")), reverse=True)
        assert [doc.doc_id for doc in result] == [2, 1, 3, 5, 4]


class TestSimilarityTransform:

    def test_transformers_score_similarity(self, mocker):
        node = mocker.Mock(spec=Node)
        similarity_scorer = HuggingFaceTransformersSimilarityScorer(ignore_doc_structure=True)
        score_similarity = ScoreSimilarity(node, similarity_scorer=similarity_scorer, query="Is this a cat?")
        dicts = [
            {"doc_id": 1, "text_representation": "Members of a strike at Yale University.", "embedding": None},
            {"doc_id": 2, "text_representation": "A woman is speaking at a podium outdoors.", "embedding": None},
        ]
        input_dataset = ray.data.from_items([{"doc": Document(doc_dict).serialize()} for doc_dict in dicts])
        execute = mocker.patch.object(node, "execute")
        execute.return_value = input_dataset
        input_dataset.show()
        output_dataset = score_similarity.execute()
        taken = output_dataset.take_all()

        for d in taken:
            doc = Document.from_row(d)
            if isinstance(doc, MetadataDocument):
                continue
            assert float(doc.properties.get("_similarity_score"))
