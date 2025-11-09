

class Entity:

    def merge_with_another_entity(self, other_entity: 'Entity') -> 'Entity':
        pass
    def merge_with(self, other_entity: 'Entity') -> 'Entity':
        pass    
    def calculate_similarity(self, other_entity: 'Entity') -> float:
        pass
    def is_compatible_with(self, other_entity: 'Entity') -> bool:
        pass
    def normalize_name(self) -> str:
        pass
    def add_property(self, key: str, value: str) -> None:
        pass
    def resolve_conflicts(self, other_entity: 'Entity') -> None:
        pass





class Relationship: