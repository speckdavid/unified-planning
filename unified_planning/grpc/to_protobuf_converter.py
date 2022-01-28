# Copyright 2021 AIPlan4EU project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import unified_planning.grpc.generated.up_pb2 as up_pb2
from unified_planning.grpc.converter import Converter, handles
import unified_planning.model
import unified_planning.plan


class ToProtobufConverter(Converter):

    @handles(unified_planning.model.Fluent)
    def _convert_fluent(self, fluent):
        name = fluent.name()
        sig = [str(t) for t in fluent.signature()]
        valType = str(fluent.type())
        return up_pb2.Fluent(name=name, valueType=valType, signature=sig)

    @handles(unified_planning.model.Object)
    def _convert_object(self, obj):
        return up_pb2.Object(name=obj.name(), type=obj.type().name())

    @handles(unified_planning.model.fnode.FNode)
    def _convert_expression(self, exp):
        payload = exp._content.payload
        value = None
        if payload is None:
            p_type = "none"
            value = "-"
        elif isinstance(payload, bool):
            p_type = "bool"
        elif isinstance(payload, int):
            p_type = "int"
        elif isinstance(payload, float):
            p_type = "real"
        elif isinstance(payload, unified_planning.model.Fluent):
            p_type = "fluent"
            value = payload.name()
        elif isinstance(payload, unified_planning.model.Object):
            p_type = "obj"
            value = payload.name()
        elif isinstance(payload, unified_planning.model.ActionParameter):
            p_type = "aparam"
            value = payload.name()
        else:
            p_type = "str"
        if value is None:
            value = str(payload)
        return up_pb2.Expression(
            type=exp._content.node_type,
            args=[self.convert(a) for a in exp._content.args],
            payload=up_pb2.Payload(type=p_type, value=value)
        )

    @handles(unified_planning.model.Effect)
    def _convert_effect(self, effect):
        x = effect.fluent()
        v = effect.value()
        return up_pb2.Assignment(x=self.convert(x), v=self.convert(v))

    @handles(unified_planning.model.InstantaneousAction)
    def _convert_instantaneous_action(self, a):
        return up_pb2.Action(
            name=a.name(),
            parameters=[p.name() for p in a.parameters()],
            parameterTypes=[p.type().name() for p in a.parameters()],
            preconditions=[self.convert(p) for p in a.preconditions()],
            effects=[self.convert(t) for t in a.effects()]
        )

    @handles(unified_planning.model.Problem)
    def _convert_problem(self, p):
        objs = []
        for t in p.user_types().keys():
            for o in p.objects(p.user_types()[t]):
                objs.append(o)

        t = p.env.expression_manager.TRUE()

        return up_pb2.Problem(
            name=p.name(),
            fluents=[self.convert(p.fluent(f)) for f in p.fluents()],
            objects=[self.convert(o) for o in objs],
            actions=[self.convert(p.action(a)) for a in p.actions()],
            initialState=[self.convert(unified_planning.model.Effect(x, v, t)) for x, v in p.initial_values().items()],
            goals=[self.convert(g) for g in p.goals()]
        )

    @handles(unified_planning.plan.ActionInstance)
    def _convert_action_instance(self, ai):
        a_msg = self.convert(ai.action())
        p_msg = [self.convert(p) for p in ai.actual_parameters()]
        return up_pb2.ActionInstance(action=a_msg, parameters=p_msg)

    @handles(unified_planning.plan.SequentialPlan, type(None))
    def _convert_sequential_plan(self, p):
        if p is None:
            return up_pb2.Answer(status=1, plan=[])
        else:
            ai_msgs = [self.convert(ai) for ai in p.actions()]
            r = up_pb2.Answer(status=0, plan=up_pb2.SequentialPlan(actions=ai_msgs))
            return r