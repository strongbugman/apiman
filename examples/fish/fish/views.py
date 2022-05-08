import json

from django.http import HttpResponse, JsonResponse
from django.views import View

from apiman.django import openapi

fishes = {
    1: {
        "id": 1,
        "name": "q",
        "age": 1,
    }
}

openapi.add_schema(
    "Fish",
    {
        "properties": {
            "id": {"description": "global unique", "type": "integer"},
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "type": "object",
        "required": ["id", "name", "age"],
    },
)


def health(req, echo):
    """
    get:
      summary: check server health
      tags:
      - manage
      parameters:
      - name: echo
        in: path
        required: True
        schema:
          type: string
      responses:
        "200":
          description: OK
    """
    openapi.validate_request(req)
    return HttpResponse(echo)


class FishView(View):
    def get(self, request):
        """
        summary: get single fish
        tags:
        - fish
        parameters:
        - name: id
          in: query
          required: True
          schema:
            type: string
        responses:
          "204":
            description: OK
          "404":
            description: Not found
        """
        openapi.validate_request(request)
        return JsonResponse(fishes[int(request.GET["id"])])

    def post(self, request):
        """
        summary: create single fish
        tags:
        - fish
        parameters:
        - name: X-Theader
          in: header
          required: True
          schema:
            type: string
        - name: x-test
          in: cookie
          required: True
          schema:
            type: string
        requestBody:
          required: true
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Fish'
        responses:
          "204":
            description: OK
          "404":
            description: Not found
        """
        openapi.validate_request(request)
        data = json.loads(request.body)
        fishes[data["id"]] = data
        return JsonResponse(data)

    @openapi.from_yaml(
        """
        summary: Delete single fish
        tags:
        - fish
        parameters:
        - name: id
          in: query
          required: True
          schema:
            type: string
        responses:
          "204":
            description: OK
          "404":
            description: Not found
        """
    )
    def delete(self, id):
        fishes.pop(id)
        return HttpResponse(status=204)
