# -*- coding: utf-8 -*-

"""
@File : actions_00033.py
@Description :自定义caitions
@Time : 2021/9/25
@Software: VSCode
"""

import json
from typing import Any, Text, Dict, List, Optional
from rasa_sdk import Action, Tracker
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, EventType, ActiveLoop
from rasa_sdk.types import DomainDict
from rasa_sdk.events import FollowupAction
from actions.global_task_00033 import DiseaseInterfaceQuery, DiseaseNameFiltering, intentRecognition, diseaseNameSimilar, collectively


query_disease = DiseaseInterfaceQuery()  # 疾病知识图谱查询
disease_filter = DiseaseNameFiltering()  # 从句子中抽出疾病
intent_recognition = intentRecognition()  # 意图识别
similar_calculator = diseaseNameSimilar()  # 看看句子里有没有相似疾病可以推荐
disease_collectively = collectively()  # 疾病统称对应的具体疾病查询
"""
以上方法是项目中用的，为了安全，源代码都删了，即便没删，因为接口访问限制，也不能运行；
理解机器人设计目的就行；
"""



class ValidateGetDiseaseForm(FormValidationAction):
    """
    对表单做一些自定义设置,与rasa1不同，这里并不是自定义Form,详见https://rasa.com/docs/rasa/forms#advanced-usage
    """
    def name(self) -> Text:
        """
        和rasa1不同，这里并不是定义的Form名称，需要在Form名字前面加个"validate_"
        """
        return "validate_get_disease_form"

    async def required_slots(
            self,
            slots_mapped_in_domain: List[Text],
            dispatcher: "CollectingDispatcher",
            tracker: "Tracker",
            domain: "DomainDict",
    ) -> List[Text]:
        """
        出入参都是官方文档指定的，这里就不详细备注了；
        按照rasa2.8的文档，可以为每个slot独立设置卡槽抽取方案，那这就有意思了，可以不用费劲替换NER组件；
        独立设置抽取方案时，需要做三件事：
            1、Define a method extract_<slot_name> for every slot that should be mapped in a custom way.
            2、Make sure that in the domain file you list for your form only those slots that use predefined mappings.
            3、Override required_slots to add all slots with custom mappings to the list of slots the form should request.
        理论上required slots可以直接从domain文件中读取，但是这里要求必须覆写required_slots方法，不知道会不会两者产生冲突，
        目前我会在这个方法里和domain文件里保持required slots一致；
        20211108日：
            关于本方法，通过查看官方样例代码后，发现实际上是给slots_mapped_in_domain(rasa从domain文件中获取的slots列表)补上一个自定义的slot，
        所以这里的操作意义应该是，除了domain里的slots，再新增一个自定义的slot，并且后续为这个slot自定义抽取方法；
            从源代码上看，所有的required slots是一个列表，rasa会对列表元素逐个抽取实体，存着实体信息的是一个字典，更新实体信息用update，
        所以如果这里新增的slot和domain里面有重名的话，自定义的抽取方法会覆盖ner组件抽出的实体；
            所以回应之前的注释，这里的冲突不会导致本例有什么bug；当然重复的实体抽取计算会提高时间复杂度，我会在domain文件里把required slots
        相关设置注释掉；
        """
        return slots_mapped_in_domain+['disease_name']

    async def extract_disease_name(
        self,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",
    ) -> Dict[Text, Any]:
        """
        这里就是上一个方法的注释里说的，define a method extract_<slot_name> for every slot that should be mapped in a custom way
        在本例中，就是自定义抽取disease_name的方法
        """
        sentence = tracker.latest_message['text']
        if disease_list:=disease_filter.disease_filter(sentence):
            return {'disease_name': disease_list[0]}
        # else:
        #     return {'disease_name': ''}


# slot:disease_name的询问方法
class AskDiseaseName(Action):
    """
    自定义的slot问法(询问方法,不是实体抽取方法)，官方文档如下：
    As soon as the form determines which slot has to be filled next by the user, it will execute the action utter_ask_<form_name>_<slot_name>
    or utter_ask_<slot_name> to ask the user to provide the necessary information. If a regular utterance is not enough,
    you can also use a custom action action_ask_<form_name>_<slot_name> or action_ask_<slot_name> to ask for the next slot.
    """
    def name(self) -> Text:
        return 'action_ask_disease_name'

    def run(self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict
    ) -> List[EventType]:
        sentence = tracker.latest_message['text']
        if collectively_list:=disease_collectively.check(sentence):
            # dispatcher.utter_message(text='请您选择其中一种疾病：')
            dispatcher.utter_message(text='请您选择其中一种疾病：', buttons=[{'title':'%s'%i,
                                               'payload':'{{"disease_name":%s}}'%i}
                                              for i in collectively_list[0]])
            # 如果有“三高”这种统称类描述,会让用户选择具体是哪种病
            # 关于button的传参:Messages starting with / are sent straight to the RegexInterpreter, 
            # which expects NLU input in a shortened /intent{entities} format.
            # 就是可以直接传递意图和实体(/后面跟意图，本例中是传递slot信息).这个button也可以在配置文件里写成模版形式.
            # 参考https://rasa.com/docs/rasa/responses#buttons

            # 这里也不要把text的内容拆出来分两步显示，会导致rasa的出参发生变化(相比使用domain里定义的button模板)，然后接口报错
        else:
            dispatcher.utter_message(text='我不是很清楚您的疾病哦，能重新描述下吗？')
            # 如果没有的话,就直接问他什么毛病
            # 注意:这里是询问slot的方法,如果用户描述的疾病被明确识别了,就不会问了,所以这里的措辞用“重新描述”没问题
        return []


# “能不能保”的回复
class ActionTakeInsurance(Action):
    """
    用户问能不能投保时的回复
    """
    def name(self) -> Text:
        return "action_take_insurance"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        disease_name = tracker.get_slot("disease_name")
        data = query_disease.search(disease_name)  # 返回数据库中的搜索结果，如果没有，会返回None

        if data:  # 能查询到疾病信息
            # =======================================我是分割符================================================
            def auxiliar_function():
                """
                因为多个逻辑分支下都要显示产品推荐，为了避免代码累赘，这里先写个辅助函数
                为什么不放在类里定义呢？因为可能涉及到tracker，data，dispacture之类的传参，感觉后期修改可能挺麻烦
                """
                if disease_name != '癌症家族史':
                    # insurance_products_recommend = data.get('products_recommended', '')
                    # 从数据库查询结果中获取该疾病的推荐保险产品
                    # 有些疾病没这个字段，就返回空字符串
                    # answer = json.dumps({"multiplelist": "猜您想问：",
                    #                      "choose": ["预核保"]+["保险产品推荐"],
                    #                      "task_template_code": "00005"})
                    # dispatcher.utter_message(answer)
                    dispatcher.utter_message(response='utter_suggest_intent')
            # =======================================我是分割符================================================

            try:
                insurance_rules = data['hbCommonsKnow']['insurance_rules']
            except KeyError or TypeError:
                insurance_rules = ''
            try:
                under_writing_rules = data['rule']
            except KeyError:
                under_writing_rules = ''
            # 数据库里，如果某些字段没有信息，查询结果就是不返回这个字段，而不是返回空值，所以这里为了避免bug，写得有点复杂


            if under_writing_rules:  # 有投保规则就展示投保规则
                dispatcher.utter_message(under_writing_rules)
                auxiliar_function()  # 按照设计，展示完投保规则后还有产品推荐
            elif insurance_rules:  # 没有投保规则，有核保规则的话，就展示核保规则
                dispatcher.utter_message(insurance_rules)
                auxiliar_function()  # 按照设计，展示完核保规则后还有产品推荐
            else:  # 核保规则也没有的话，就返回兜底回复
                dispatcher.utter_message("已经记录下您的问题啦，正在努力刻苦学习中~")
                return [FollowupAction('action_restart')]
        else:  # 查不到疾病信息的话，就返回兜底回复
            dispatcher.utter_message("已经记录下您的问题啦，正在努力刻苦学习中~")
            return [FollowupAction('action_restart')]
        return []


# “预核保”的回复
class ActionPreUnderWriting(Action):
    """
    用户问预核保时的回复
    """
    def name(self) -> Text:
        return "action_pre_underwriting"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        disease_name = tracker.get_slot("disease_name")
        data = query_disease.search(disease_name)  # 返回数据库中的搜索结果，如果没有，会返回None
        if data:
            dispatcher.utter_message(data.get("rule", ''))  # 产品设计里，这里应该展示常见核保结论，但是没看到这字段，最接近的就是“rule”核保规则
            dispatcher.utter_message(data.get("introductory", ''))  # 产品设计里，这里展示疾病科普，也没看到这个字段，最接近的是“introductory”疾病介绍
            dispatcher.utter_message(data.get("cover_material", ''))  # 展示投保资料
        else:  # 查不到这个疾病的相关信息，就返回兜底回复
            dispatcher.utter_message("已经记录下您的问题啦，正在努力刻苦学习中~")
            return [FollowupAction('action_restart')]
        return []


# “产品推荐”的回复
class ActionProductsRecommend(Action):
    """
    用户问产品推荐时的回复
    """
    def name(self) -> Text:
        return "action_products_recommend"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        disease_name = tracker.get_slot("disease_name")
        data = query_disease.search(disease_name)  # 返回数据库中的搜索结果，如果没有，会返回None
        if data:
            insurance_products_recommend = data.get('products_recommended', '')
            if insurance_products_recommend:
                dispatcher.utter_message(insurance_products_recommend)
            else:
                dispatcher.utter_message("目前还没有相关产品推荐哦，正在努力学习中~")
        else:
            dispatcher.utter_message("目前还没有相关产品推荐哦，正在努力学习中~")
        return []


# 保中患病
class ActionSickInSail(Action):
    """
    用户问保中患病时的回复
    """
    def name(self) -> Text:
        return "action_sick_in_sail"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        disease_name = tracker.get_slot("disease_name")
        data = query_disease.search(disease_name)  # 返回数据库中的搜索结果，如果没有，会返回None
        if data:
            dispatcher.utter_message(data.get("etiology", ''))  # “etiology”病因
            dispatcher.utter_message(data.get("article01", ''))  # “article01”生活护理
            dispatcher.utter_message(data.get("qa", ''))  # “qa”求医问诊
        else:  # 查不到这个疾病的相关信息，就返回兜底回复
            dispatcher.utter_message("已经记录下您的问题啦，正在努力刻苦学习中~")
            return [FollowupAction('action_restart')]
        return []





















