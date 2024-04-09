from sycamore.data import BoundingBox, Document, Element


class TestElement:
    def test_element(self):
        element = Element()
        assert element.type is None
        assert element.text_representation is None
        assert element.binary_representation is None
        assert element.bbox is None
        assert element.properties == {}

        element.type = "table"
        element.text_representation = "text"
        element.bbox = BoundingBox(1, 2, 3, 4)
        element.properties.update({"property1": 1})
        assert element.type == "table"
        assert element.text_representation == "text"
        assert element.properties == {"property1": 1}

        element.properties.update({"property2": 2})
        assert element.properties == {"property1": 1, "property2": 2}

        del element.properties
        assert element.properties == {}
        assert element.data["bbox"] == (1, 2, 3, 4)


class TestDocument:
    def test_document(self):
        document = Document()
        assert document.doc_id is None
        assert document.type is None
        assert document.text_representation is None
        assert document.binary_representation is None
        assert document.elements == []
        assert document.embedding is None
        assert document.parent_id is None
        assert document.bbox is None
        assert document.properties == {}

        document.doc_id = "doc_id"
        document.type = "table"
        document.text_representation = "text"
        element1 = Element()
        document.elements = [element1]
        document.embedding = [[1.0, 2.0], [2.0, 3.0]]
        document.bbox = BoundingBox(1, 2, 3, 4)
        document.properties["property1"] = 1
        assert document.doc_id == "doc_id"
        assert document.type == "table"
        assert document.text_representation == "text"
        assert document.elements == [element1.data]
        assert document.embedding == [[1.0, 2.0], [2.0, 3.0]]
        assert document.properties == {"property1": 1}
        document.properties = {"property2": 2}
        assert len(document.properties) == 1
        assert document.properties == {"property2": 2}

        element2 = Element({"type": "image", "text": "text"})
        document.elements = [element1, element2]
        assert document.elements == [element1.data, element2.data]
        document.properties["property3"] = 3
        document.properties.update({"property4": 4})
        assert document.properties == {"property2": 2, "property3": 3, "property4": 4}

        del document.elements
        del document.properties
        assert document.elements == []
        assert document.properties == {}

        assert document.data["bbox"] == (1, 2, 3, 4)

    def test_serde(self):
        dict = {
            "doc_id": "doc_id",
            "type": "pdf",
            "text_representation": "text_representation",
            "bbox": (1, 2.3, 3.4, 4.5),
            "elements": [
                {
                    "type": "table",
                    "bbox": (1, 2, 3, 4.0),
                },
                {
                    "type": "figure",
                    "bbox": (1, 2, 3, 4.0),
                },
            ],
            "properties": {"int": 0, "float": 3.14, "list": [1, 2, 3, 4], "tuple": (1, "tuple")},
        }
        document = Document(dict)
        serde = Document(document.serialize())
        assert serde.data == dict
