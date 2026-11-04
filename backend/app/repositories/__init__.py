"""数据访问层：所有 SQL / ORM 操作集中在这里。

约定：
  - 只做查询与持久化，返回 ORM 对象或元组，不含业务判断；
  - 只 flush，不 commit（事务边界由 service 控制）；
  - 不抛 HTTP 状态码，找不到就返回 None。
"""
