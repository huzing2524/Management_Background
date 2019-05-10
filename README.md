<table>
   <tr>
      <td>API</td>
      <td>任务 resource </td>
      <td>操作 type </td>
      <td>资源 params </td>
      <td>说明</td>
      <td>发送消息</td>
   </tr>
   <tr>
      <td rowspan="1">/bg/dsd/grant</td>
      <td>BgDSDGrant</td>
      <td>POST</td>
      <td>{
  "id": "string",
  "dsd_val": 0
}</td>
      <td>赠送给id成功</td>
      <td> :white_check_mark: </td>
   </tr>
   <tr>
      <td rowspan="1">/bg/examine/{id}</td>
      <td>BgExamine</td>
      <td>POST</td>
      <td>{"id": "string", "state": "string", "state_msg": "string"} </td>
      <td>申请加入智能制造</td>
      <td> :white_check_mark: </td>
   </tr>
   <tr>
   <td rowspan="1">/bg/auth</td>
      <td>BgAuth</td>
      <td>POST</td>
      <td>{"id": "string","state": "string","msg": "string"}</td>
      <td>用户信息认证</td>
      <td> :white_check_mark: </td>
   </tr>
   <tr>
      <td rowspan="1">/facs/modify</td>
      <td>BgFacsModify</td>
      <td>POST</td>
      <td>{
  "id": "string",
  "name": "string",
  "title": "string",
  "administrators": [
    "15555555555"
  ]
}</td>
      <td>企业信息修改成功</td>
      <td> :white_check_mark: </td>
   </tr>
   <tr>
      <td rowspan="1">/bg/feedback/resp</td>
      <td>BgFeedbackResp</td>
      <td>POST</td>
      <td>{
  "id": "string",
  "msg": "string"
}</td>
      <td>用户反馈回复</td>
      <td> :white_check_mark: </td>
   </tr>
   <tr>
      <td rowspan="1">/bg/xd/images/tag</td>
      <td>BgXDImagesTag</td>
      <td>PUT</td>
      <td>{
  "id": int,
  "res": "string",
  "err_reason": "string"
}</td>
      <td>用户图片审核</td>
      <td> :white_check_mark: </td>
   </tr>
   
   
</table>