# Rasa2.8.14官方docker镜像保姆级使用教程

# 写在前面:  
&ensp;&ensp;&ensp;&ensp;1、x86_64 Linux和Intel Mac下，下述指南可无障碍跑通；ARM服务器未测试，大概率是不行的，原因参考第2点；  
&ensp;&ensp;&ensp;&ensp;2、Apple Silicon平台下打包镜像时需要指定platform为linux/amd64，以便在x86服务器上正常运行；Apple Silicon平台下无法调试和运行，因为rasa2.8使用的tf、pd等底层涉及到C++的模块在arm架构下不能正常编译，得等后续更新；    
&ensp;&ensp;&ensp;&ensp;3、x86_64 Windows平台下，以下命令请在wsl shell中执行，可无障碍跑通；  
&ensp;&ensp;&ensp;&ensp;4、Docker在win上本身就是运行于wsl2，请不要有什么必须用win terminal开发的强迫症。如果真的浑身难受，把文件映射的$(pwd)命令改成适用win的形式就行，具体实现自行搜索；  
&ensp;&ensp;&ensp;&ensp;5、在本文档中附上了所有用到的镜像的Dockerfile，如有需要可以修改并重新build；  
&ensp;&ensp;&ensp;&ensp;6、项目设计是多个机器人放在同一个项目文件夹下，共用rasa action server，所以每个机器人的训练数据和模型文件都单独保存了，如果你不需要，就不用这么麻烦；
<br/>  

# 所有的代码和配置文件均添加了海量注释
# 项目并不能直接跑通(有机密数据，删了)，重在学习
# 因为官方docker镜像使用说明有点乱，并且也搜不到靠谱的方案，在这里记录自己的心得
# 需要一定的阅读时间，应答机器人的需求多种多样，本来也很难让你复制粘贴并傻瓜式运行

# 一、开发一个机器人

&ensp;&ensp;&ensp;&ensp;1. 自定义action写在actions文件夹下,以机器人id为后缀,如actions_00033.py;  
&ensp;&ensp;&ensp;&ensp;2. 对应数据、配置文件在data文件夹中新建一个文件夹并保存,如新建一个00033文件夹,并存放config、domain、nlu、rules、stories文件（sources文件夹下的total_word_feature_extractor_zh.dat已删除，因为github限制文件体积）;  
&ensp;&ensp;&ensp;&ensp;3. 对应的模型数据,在根目录的models（如果没有，则新建一个）文件夹下新建一个文件夹,如新建一个00033文件夹,在模型训练的时候,指定这个文件夹为模型保存地址;  
&ensp;&ensp;&ensp;&ensp;4. 如果需要保存日志,在logs（如果没有，则新建一个）文件夹下新建一个与机器人id同名的文件夹,如00033,每个机器人的日志保存在自己对应的位置;  
&ensp;&ensp;&ensp;&ensp;5. 如何使用rasa开发,参考https://rasa.com/docs/rasa/；；  
&ensp;&ensp;&ensp;&ensp;6. 在项目根目录中的docker-compose.yml文件中，新增新机器人的容器，记得给这个新容器取名，如rasabot_00033；  


# 二、模型训练
&ensp;&ensp;&ensp;&ensp;在终端进入到本项目根目录下，运行(以机器人id 00033为例，下同，后续不再赘述):
```
    docker run --name trainer -u root -v $(pwd):/app rasa/rasa:2.8.14-full train --data data/00033 --config data/00033/config.yml --domain data/00033/domain.yml --out models/00033 --num-threads 5
```
>Tips:
1. rasa官方镜像的用户是1001,不是root,因为训练模型之后要写入模型文件,所以docker run后面要加个-u root参数，不然会提示权限错误；  
2. 顺便给这个容器起个名“trainer”，方便事后删除容器；  
3. 上述命令定制了训练数据地址、配置文件地址和模型保存地址，更多命令可参考官方文档,酌情更改。

# 三、单独测试RASA NLU组件
&ensp;&ensp;&ensp;&ensp;在终端进入到本项目根目录下的Intelligent_task_model_rasa2文件夹下，运行: （指定了模型文件地址，酌情修改；容器名“shell-test-nlu”，方便事后删除，下文不再赘述）
```
    docker run -it -u root --name shell-test-nlu -v $(pwd):/app rasa/rasa:2.8.14-full shell nlu -m models/00033
````

# 四、测试完整的RASA服务(rasa server和rasa action server)
&ensp;&ensp;&ensp;&ensp;在终端进入到本项目根目录下  
&ensp;&ensp;&ensp;&ensp;1. 新建桥接器:  
```
    docker network create rasa2_bot  
```  

&ensp;&ensp;&ensp;&ensp;2. 启动rasa actions服务: （必要的一步！不能少！我刚开始就只看到了shell命令，rasa文档把这一步写在了shell命令说明的后面，排查了好久） 
```
    docker run -d -v $(pwd)/actions:/app/actions --net rasa2_bot --name action-server rasa/rasa-sdk:2.8.2 
```
>&ensp;&ensp;&ensp;&ensp;注：如果有自定义的需求，如一些其他依赖，可以基于官方的rasa sdk镜像重新制作打包，在sources文件夹中有Dockerfile可供参考；rasaSDK版本是和rasa版本对应的，如有需要，酌情修改。  

&ensp;&ensp;&ensp;&ensp;3. 启动rasa服务并进入shell测试状态（指定了模型文件地址；指定了端口映射；如有需要，酌情修改）:
````
    docker run -it -v $(pwd):/app -p 5005:5005 --net rasa2_bot --name rasa-server rasa/rasa:2.8.14-full shell --model models/00033
````
>&ensp;&ensp;&ensp;&ensp;注：一样的，也可以自定义镜像。 

>Tips:  
1. 可以通过查看action-server容器的日志来排查action相关错误,不要局限于rasa的报错;  
2. 可以在启动rasa服务的命令末尾加上--debug来查看更详尽的日志,为了方便复制粘贴，这里直接把整个命令贴上来:
````
    docker run -it -v $(pwd):/app -p 5005:5005 --net rasa2_bot --name rasa-server rasa/rasa:2.8.14-full shell --model models/00033 --debug
````



# 五、启动服务(rasa server、rasa action server、intelligent_main)  
&ensp;&ensp;&ensp;&ensp;在终端进入到本项目根目录下,直接运行:
```  
    docker-compose up
```

# 六、访问rasa服务
&ensp;&ensp;&ensp;&ensp;现在，你可以使用post来访问rasa服务了，贴上一段Python代码以供参考： 
```` 
headers = {'Content-type': 'application/json'}  
url = 'http://127.0.0.1:5005/webhooks/rest/webhook'  
data = {'sender': sender_id,'message': question}  
response = requests.post(url=url, json=data, headers=headers)  
response = json.loads(response.content)  
````
rasa接受的参数为用户id和问题，更具体的，请参考官方文档https://rasa.com/docs/rasa/


# 七、终止服务  
&ensp;&ensp;&ensp;&ensp;在终端进入到本项目根目录下,直接运行: 
``` 
    docker-compose down  
```