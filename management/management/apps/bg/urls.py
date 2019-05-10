# -*- coding: utf-8 -*-

from django.conf.urls import url


from bg import views_bg_V230, views_bg_V300, views_bg_V310, views_bg_V330, views_bg_V340

urlpatterns = [
    # V2.3.0------------------------------------------------------------------------------------------------------------
    url(r"^password", views_bg_V230.Password.as_view()),
    url(r"^image/test", views_bg_V230.ImageTest.as_view()),
    url(r"^bg/login", views_bg_V230.Login.as_view()),
    url(r"^bg/list", views_bg_V230.BgList.as_view()),
    url(r"^bg/auth", views_bg_V230.Auth.as_view()),
    url(r"^bg/file", views_bg_V230.File.as_view()),
    url(r"^bg/facs/names", views_bg_V230.FactoryNames.as_view()),
    url(r"^bg/user/list", views_bg_V230.UserList.as_view()),
    url(r"^bg/user/stats", views_bg_V230.UserStatus.as_view()),
    url(r"^bg/dsd/grant", views_bg_V230.DsdGrant.as_view()),
    url(r"^bg/dsd/list", views_bg_V230.DsdList.as_view()),
    url(r"^bg/feedback/list", views_bg_V230.FeedbackList.as_view()),
    url(r"^bg/feedback/resp", views_bg_V230.FeedBackResp.as_view()),
    url(r"^bg/examine/list", views_bg_V230.ExamineList.as_view()),
    url(r"^bg/examine/(\d{11})", views_bg_V230.ExamineId.as_view()),

    # V3.0.0------------------------------------------------------------------------------------------------------------
    url(r"^bg/apps/state/(\w+)", views_bg_V300.BgAppsState.as_view()),
    url(r"^bg/apps/(\w+)", views_bg_V300.BgAppsModify.as_view()),
    url(r"^bg/apps", views_bg_V300.BgApps.as_view()),
    url(r"^bg/manufacturing/market/list", views_bg_V300.MarketList.as_view()),
    url(r"^bg/manufacturing/finance/list", views_bg_V300.FinanceList.as_view()),
    url(r"^bg/manufacturing/material/list", views_bg_V300.MaterialList.as_view()),
    url(r"^bg/manufacturing/products/list", views_bg_V300.ProductsList.as_view()),
    url(r"^bg/manufacturing/store/list", views_bg_V300.StoreList.as_view()),
    url(r"^bg/xd/tasks/(\w+)$", views_bg_V300.XDTask.as_view()),
    url(r"^bg/xd/tasks", views_bg_V300.XDTask.as_view()),
    url(r"^bg/xd/images/tag/keyword", views_bg_V300.XDImageTagKW.as_view()),
    url(r"^bg/xd/images/tag/(\w+)$", views_bg_V300.XDImageTag.as_view()),
    url(r"^bg/xd/images/tag", views_bg_V300.XDImageTag.as_view()),

    # V3.1.0------------------------------------------------------------------------------------------------------------
    url(r"^bg/rights/list", views_bg_V310.BgRightsList.as_view()),
    url(r"^bg/rights/new", views_bg_V310.BgRightsNew.as_view()),
    url(r"^bg/rights/del", views_bg_V310.BgRightsDel.as_view()),
    url(r"^bg/rights/password", views_bg_V310.BgRightsPassword.as_view()),
    url(r"^bg/rights/name", views_bg_V310.BgRightsName.as_view()),
    url(r"^bg/facs/list", views_bg_V310.FactoryList.as_view()),
    url(r"^bg/facs/new", views_bg_V310.FactoryNew.as_view()),
    url(r"^bg/facs/del", views_bg_V310.FactoryDelete.as_view()),
    url(r"^bg/facs/modify", views_bg_V310.FactoryModify.as_view()),
    url(r"^bg/facs/admins/del/(?P<factory_id>(\w)+)/(?P<administrators>(\w)+)", views_bg_V310.BgAdminsDelete.as_view()),
    url(r"^bg/facs/admins", views_bg_V310.BgAdmins.as_view()),

    # V3.3.0------------------------------------------------------------------------------------------------------------
    url(r"^bg/industry_plus/examine", views_bg_V330.BgIndustryPlusExamineList.as_view()),
    url(r"^bg/industry_plus/test", views_bg_V330.BgIndustryPlusTestList.as_view()),

    # V3.3.0------------------------------------------------------------------------------------------------------------
    url(r"^bg/banner", views_bg_V340.BgBanner.as_view()),
    url(r"^bg/invite/friend/list", views_bg_V340.BgInviteFriendList.as_view()),
    url(r"^bg/invite/factory/list", views_bg_V340.BgInviteFactoryList.as_view()),
]
