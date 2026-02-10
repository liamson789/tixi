from rest_framework import serializers

class ReserveSerializer(serializers.Serializer):
    raffle_id = serializers.IntegerField()
    numbers = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class AvailableNumbersSerializer(serializers.Serializer):
    list_id = serializers.IntegerField()
    available_numbers = serializers.ListField(child=serializers.IntegerField())
