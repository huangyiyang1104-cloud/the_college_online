"""业务服务层：承载业务规则与事务边界。

约定：service 里不出现 select() / db.get()，数据访问一律走 repositories/；
响应包装（code/message/data）由 controller 负责，service 只返回业务数据。
"""
