/**
 * isMobile
 * headerFixed
 * responsiveMenu
 * themesflatSearch
 * detectViewport
 * blogLoadMore
 * commingsoon
 * goTop
 * retinaLogos
 * customizable_carousel
 * parallax
 * iziModal
 * bg_particles
 * pagetitleVideo
 * toggleExtramenu
 * removePreloader
 */

(function ($) {
    "use strict";

    var isMobile = {
        Android: function () {
            return navigator.userAgent.match(/Android/i);
        },
        BlackBerry: function () {
            return navigator.userAgent.match(/BlackBerry/i);
        },
        iOS: function () {
            return navigator.userAgent.match(/iPhone|iPad|iPod/i);
        },
        Opera: function () {
            return navigator.userAgent.match(/Opera Mini/i);
        },
        Windows: function () {
            return navigator.userAgent.match(/IEMobile/i);
        },
        any: function () {
            return (
                isMobile.Android() ||
                isMobile.BlackBerry() ||
                isMobile.iOS() ||
                isMobile.Opera() ||
                isMobile.Windows()
            );
        },
    };

    var Modal_Right = function () {
        const body = $("body");
        const modalMenu = $(".modal-menu-left");
        const modalMenuBody = modalMenu.children(".modal-menu__body");

        if (modalMenu.length) {
            const open = function () {
                modalMenu.addClass("modal-menu--open");
            };
            const close = function () {
                modalMenu.removeClass("modal-menu--open");
            };

            $(".modal-menu-left-btn").on("click", function () {
                open();
            });
            $(".modal-menu__backdrop, .modal-menu__close").on(
                "click",
                function () {
                    close();
                }
            );
        }

        modalMenu.on("click", function (event) {
            const trigger = $(this);
            const item = trigger.closest("[data-modal-menu-item]");
            let panel = item.data("panel");

            if (!panel) {
                panel = item
                    .children("[data-modal-menu-panel]")
                    .children(".modal-menu__panel");

                if (panel.length) {
                    modalMenuBody.append(panel);
                    item.data("panel", panel);
                    panel.width(); // force reflow
                }
            }

            if (panel && panel.length) {
                event.preventDefault();
            }
        });
        $(".modal-menu__body #mainnav-secondary .menu li").each(function (n) {
            if (
                $(".modal-menu__body #mainnav-secondary .menu li:has(ul)").find(
                    ">span"
                ).length == 0
            ) {
                $(
                    ".modal-menu__body #mainnav-secondary .menu li:has(ul)"
                ).append('<span class="icon-monal-arrow-right-2"></span>');
            }
            $(this).find(".sub-menu").css({ display: "none" });
        });
        $(".modal-menu__body  #mainnav-secondary .menu li:has(ul) > span").on(
            "click",
            function (e) {
                e.preventDefault();
                $(this).closest("li").children(".sub-menu").slideToggle();
                $(this).closest("li").toggleClass("opened");
            }
        );
    };

    var menu_Modal_Left = function () {
        var menuType = "desktop";

        // $(window).on("load resize", function () {
            var currMenuType = "desktop";
            var adminbar = $("#wpadminbar").height();

            if (matchMedia("only screen and (max-width: 991px)").matches) {
                currMenuType = "mobile";
            }

            if (currMenuType !== menuType) {
                menuType = currMenuType;

                if (currMenuType === "mobile") {
                    var $mobileMenu = $("#mainnav").hide();
                    var hasChildMenu = $(".mainnav_canvas").find("li:has(ul)");
                    hasChildMenu.children("ul").hide();
                    if (hasChildMenu.find(">span").length == 0) {
                        hasChildMenu
                            .children("a")
                            .after('<span class="btn-submenu"></span>');
                    }
                    $(".btn-menu").removeClass("active");
                   
                    $(".canvas-nav-wrap .canvas-menu-close").css({
                        top: adminbar + 30,
                    });
                } else {
                    var $mobileMenu = $("#mainnav").show();
                    
                    $(".canvas-nav-wrap .canvas-menu-close").css({
                        top: adminbar + 30,
                    });
                    $("#header").find(".canvas-nav-wrap").removeClass("active");
                }
            }
        // });

        $(".btn-menu").on("click", function (e) {
            $(this)
                .closest("body")
                .find(".canvas-nav-wrap")
                .addClass("active");
        });

        $(window).scroll(function(event){
            $(".canvas-nav-wrap").removeClass("active");
         });

        $(".canvas-nav-wrap .overlay-canvas-nav").on("click", function (e) {
            $(this)
                .closest("#header")
                .find(".canvas-nav-wrap")
                .removeClass("active");
        });

        $(document).on(
            "click",
            ".mainnav_canvas li .btn-submenu",
            function (e) {
                $(this).toggleClass("active").next("ul").slideToggle(300);
                e.stopImmediatePropagation();
            }
        );
    };

    var menu_category = function () {
        var menuType = "desktop";

        $(window).on("load resize", function () {
            var currMenuType = "desktop";
            var adminbar = $("#wpadminbar").height();

            if (matchMedia("only screen and (max-width: 991px)").matches) {
                currMenuType = "mobile";
            }

            if (currMenuType !== menuType) {
                menuType = currMenuType;

                if (currMenuType === "mobile") {
                    var $mobileMenu = $("#mainnav").hide();
                    var hasChildMenu = $(".mainnav_canvas").find("li:has(ul)");
                    hasChildMenu.children("ul").hide();
                    if (hasChildMenu.find(">span").length == 0) {
                        hasChildMenu
                            .children("a")
                            .after('<span class="btn-submenu"></span>');
                    }
                    $(".btn-menu").removeClass("active");
                    
                    $(".canvas-nav-wrap .canvas-menu-close").css({
                        top: adminbar + 30,
                    });
                } else {
                    var $mobileMenu = $("#mainnav").show();
                    
                    $(".canvas-nav-wrap .canvas-menu-close").css({
                        top: adminbar + 30,
                    });
                    $("#header").find(".canvas-nav-wrap").removeClass("active");
                }
            }
        });

        $(".btn-menu").on("click", function (e) {
            $(this)
                .closest("#header")
                .find(".canvas-nav-wrap")
                .addClass("active");
        });

        $(".canvas-nav-wrap .overlay-canvas-nav").on("click", function (e) {
            $(this)
                .closest("#header")
                .find(".canvas-nav-wrap")
                .removeClass("active");
        });

        $(document).on(
            "click",
            ".mainnav_canvas li .btn-submenu",
            function (e) {
                $(this).toggleClass("active").next("ul").slideToggle(300);
                e.stopImmediatePropagation();
            }
        );
    };

    function tf_ToggleMiniCartType(toggle_type){
        var toggle_element = $('.nav-shop-cart, body'),
            toggle_class   = 'active-minicart';

        if(toggle_type == 'show'){
            toggle_element.addClass(toggle_class);
        }
        else if(toggle_type == 'hide'){
            toggle_element.removeClass(toggle_class);
        }
        else{
            toggle_element.toggleClass('active-minicart');
        }
        
    } 


    var headerFixed = function () {
        if ($("body").hasClass("header_sticky")) {
            var header = $("#header-fixed-wrap"),
                hd_height = $("#header").height(),
                height = $("#header").outerHeight(),
                wpadminbar = $("#wpadminbar").height(),
                injectSpace = $("<div />", { height: hd_height }).insertAfter(
                    $("#header")
                );
            injectSpace.hide();
            var lastScroll = 0;

            $(window).on("load scroll resize", function () {
                
                    var top_height = $(".themesflat-top").height(),
                        wpadminbar = $("#wpadminbar").height();
                    if (top_height == undefined) {
                        top_height = 0;
                    }
                    if (matchMedia("only screen and (max-width: 300px)").matches) {
                        if ($(window).scrollTop() >= top_height + wpadminbar) {
                            header.addClass("header-sticky");
                            $(".header-sticky").removeAttr("style");
                            // injectSpace.show();
                        } else {
                            $(".header-sticky").removeAttr("style");
                            header.removeClass("header-sticky");
                            injectSpace.hide();
                            $("#wpadminbar").css('z-index','999999');
                        }
                    } else {
                        if ($(window).scrollTop() >= top_height + hd_height) {
                            header.addClass("header-sticky");
                            // injectSpace.show();
                        } else {
                            $(".header-sticky").removeAttr("style");
                            header.removeClass("header-sticky");
                            injectSpace.hide();
                            $("#wpadminbar").css('z-index','999999');
                        }
                    }
               
                

        
                $(window).scroll(function(){
                    var scroll = $(window).scrollTop();

                    if (scroll > lastScroll   ) {
                        header.removeClass("active").removeAttr("style");
                    } else if ( scroll < lastScroll ) {
                        header.addClass("active").css("top", wpadminbar);
                        tf_ToggleMiniCartType('hide');
                    }
                    
                    lastScroll = scroll;

                    if ( $(window).scrollTop() < top_height + hd_height ) {
                        header.removeClass("active").removeAttr("style");
                    }
                    
                });
            });
        }
    };

    var themesflatSearch = function () {
        $(document).on("click", function (e) {
            var clickID = e.target.id;
            if (clickID != "s") {
                $(".top-search").removeClass("show");
                $(".show-search").removeClass("active");
            }
        });

        $(".show-search").on("click", function (event) {
            event.stopPropagation();
        });

        $(".search-form").on("click", function (event) {
            event.stopPropagation();
        });

        $(".show-search").on("click", function (e) {
            if (!$(this).hasClass("active")) $(this).addClass("active");
            else $(this).removeClass("active");
            e.preventDefault();

            if (!$(".top-search").hasClass("show"))
                $(".top-search").addClass("show");
            else $(".top-search").removeClass("show");
        });
    };

    var pagetitleVideo = function () {
        if ($(".page-title").hasClass("video")) {
            jQuery(function () {
                jQuery("#ptbgVideo").YTPlayer();
            });
        }
    };

    var Category_menu = function (e) {
        
       $(".nav-wrap-category .title-menu").on('click', function(){
            if($(".nav-wrap-category .category-menu").hasClass('active')) {
                $(".nav-wrap-category .category-menu").removeClass('active');
                $(".nav-wrap-category .category-menu").hide();
            }
            else {
                $(".nav-wrap-category .category-menu").addClass('active');
                $(".nav-wrap-category .category-menu").show();
            }
        });
        
    };
    $(document).on("click", function(event) {
        if ($(event.target).closest(".nav-wrap-category").length === 0) {
            $(".nav-wrap-category .category-menu").removeClass('active');
            $(".nav-wrap-category .category-menu").hide();
          }
      });

    var blogLoadMore = function () {
        var $container = $(".wrap-blog-article");
        if ($("body").hasClass("page-template")) {
            var $container = $(".wrap-blog-article");
        }
        var $container = $(".wrap-blog-article");

        $(".navigation.loadmore.blog a").on("click", function (e) {
            var page = 2;

            e.preventDefault();
            var $item = ".item";
            $("<span/>", {
                class: "infscr-loading",
                text: "Loading...",
            }).appendTo($container);

            $.ajax({
                type: "GET",
                url: $(this).attr("href"),
                dataType: "html",
                data: {
                    action: "load_posts_by_ajax",
                    page: page,
                    security: blog.security,
                },
                success: function (out) {
                    var result = $(out).find($item);
                    var nextlink = $(out)
                        .find(".navigation.loadmore.blog a")
                        .attr("href");

                    result.css({ opacity: 0 });
                    if ($container.hasClass("blog-masonry")) {
                        $container.append(result).imagesLoaded(function () {
                            result.css({ opacity: 1 });
                            $container.masonry("appended", result);
                        });
                    } else {
                        result.css({ opacity: 1 });
                        $container.append(result);
                    }

                    if (nextlink != undefined) {
                        $(".navigation.loadmore.blog a").attr("href", nextlink);
                        $container.find(".infscr-loading").remove();
                    } else {
                        $container
                            .find(".infscr-loading")
                            .addClass("no-ajax")
                            .text("All posts loaded.")
                            .delay(2000)
                            .queue(function () {
                                $(this).remove();
                            });
                        $(".navigation.loadmore.blog").remove();
                    }
                    customizable_carousel();
                    iziModal();
                },
            });
        });
    };

    var goTop = function () {
        $(window).scroll(function () {
            if ($(this).scrollTop() > 500) {
                $(".go-top").addClass("show");
            } else {
                $(".go-top").removeClass("show");
            }
        });

        $(".go-top").on("click", function (event) {
            event.preventDefault();
            $("html, body").animate({ scrollTop: 0 }, 0);
        });
    };

    var customizable_carousel_div = function () {
        var owl_carousel = $("div.customizable-carousel");
        if (owl_carousel.length > 0) {
            owl_carousel.each(function () {
                var $this = $(this),
                    $items = $this.data("items") ? $this.data("items") : 1,
                    $loop = $this.attr("data-loop") ? $this.data("loop") : true,
                    $navdots = $this.data("nav-dots")
                        ? $this.data("nav-dots")
                        : false,
                    $navarrows = $this.data("nav-arrows")
                        ? $this.data("nav-arrows")
                        : false,
                    $autoplay = $this.attr("data-autoplay")
                        ? $this.data("autoplay")
                        : false,
                    $autospeed = $this.attr("data-autospeed")
                        ? $this.data("autospeed")
                        : 3500,
                    $smartspeed = $this.attr("data-smartspeed")
                        ? $this.data("smartspeed")
                        : 950,
                    $autohgt = $this.data("autoheight")
                        ? $this.data("autoheight")
                        : false,
                    $space = $this.attr("data-space")
                        ? $this.data("space")
                        : 15;

                $(this).owlCarousel({
                    loop: $loop,
                    items: $items,
                    responsive: {
                        0: {
                            items: $this.data("xs-items")
                                ? $this.data("xs-items")
                                : 1,
                            nav: false,
                        },
                        600: {
                            items: $this.data("sm-items")
                                ? $this.data("sm-items")
                                : 2,
                            nav: false,
                        },
                        1000: {
                            items: $this.data("md-items")
                                ? $this.data("md-items")
                                : 3,
                        },
                        1240: {
                            items: $items,
                        },
                    },
                    dots: $navdots,
                    autoplayTimeout: $autospeed,
                    smartSpeed: $smartspeed,
                    autoHeight: $autohgt,
                    margin: $space,
                    nav: $navarrows,
                    navText: [
                        '<i class="fa fa-angle-left"></i>',
                        '<i class="fa fa-angle-right"></i>',
                    ],
                    autoplay: $autoplay,
                    autoplayHoverPause: true,
                });
            });
        }
    };

    var bg_bottom = function () {
        $(window).on("load resize", function () {
            var width_span = $(".copyright span").outerWidth() + 100;
            $(".bottom .bg_copyright").css("min-width", width_span);
        });
    };

    var tfvideo = function () {
        $(".btn-video").magnificPopup({
            fixedContentPos: true,
            closeOnContentClick: true,
            closeBtnInside: false,
            type: "iframe",
            mainClass: "mfp-fade",
            removalDelay: 160,
            preloader: false,
        });
    };

    var productCarousel = function() {
        if ( $().owlCarousel ) {
            $('.related-product.has-carousel').each(function(){
                var
                $this = $(this),
                item = $this.data("column"),
                item2 = $this.data("column2"),
                item3 = $this.data("column3"),
                item4 = $this.data("column4")

                $this.find('.owl-carousel').owlCarousel({
                    loop: false,
                    margin: 15,
                    nav: true,
                    dots: false,
                    navText: ["<div class='nav-button owl-prev'>‹</div>", "<div class='nav-button owl-next'>›</div>"],
                    responsive: {
                        0:{
                            items:item4
                        },
                        500:{
                            items:item3
                        },
                        768:{
                            items:item2
                        },
                        1000:{
                            items:item
                        }
                    }
                });

            });
        }
    } 

    var tftabs = function() {   
     
        $('.tf-tabs').each( function() {
            
            $(this).find('.tf-tabnav ul > li').filter(':first').addClass('active').removeClass('inactive');
            $(this).find('.tf-tabcontent').children().filter(':first').addClass('active');

            
            if ( $(this).find('.tf-tabnav ul > li').hasClass('set-active-tab') ) {
                $(this).find('.tf-tabnav ul > li').siblings().removeClass('active');                
            }
            if ( $(this).find('.tf-tabcontent').children().hasClass('set-active-tab') ) {
                $(this).find('.tf-tabcontent').children().siblings().removeClass('active');
            }

            $(this).find('.tf-tabnav ul > li').on('click', function(){
                var tab_id = $(this).attr('data-tab');

                $(this).siblings().removeClass('active').removeClass('set-active-tab').addClass('inactive');
                $(this).closest('.tf-tabs').find('.tf-tabcontent').children().removeClass('active').removeClass('set-active-tab').addClass('inactive');

                $(this).addClass('active').removeClass('inactive');
                $(this).closest('.tf-tabs').find('.tf-tabcontent').children('#'+tab_id).addClass('active').removeClass('inactive');
            });
        });
    }
    
    var tf_language = function() {
        $('.flat-language .unstyled-child li  a').on("click", function(event) {
            var a = $(this).text();
           $(this).closest(".current").children('a').text(a);
          });
    }

    var custom_select = function() {
        $('select#product_cat').each(function(){
               var $this = $(this), selectOptions = $(this).children('option').length;
             
               $this.addClass('hide-select'); 
               $this.after('<div class="tf-select-custom"></div>');

               var $customSelect = $this.next('div.tf-select-custom');
               $customSelect.text($this.children('option').eq(0).text());
             
               var $optionlist = $('<ul class="select-options" /><div class="header-select-option"><span>Select Categories</span><span class="close-option"><svg width="24" height="24" aria-hidden="true" role="img" focusable="false" viewBox="0 0 32 32"><path d="M28.336 5.936l-2.272-2.272-10.064 10.080-10.064-10.080-2.272 2.272 10.080 10.064-10.080 10.064 2.272 2.272 10.064-10.080 10.064 10.080 2.272-2.272-10.080-10.064z"></path></svg></span></div>').insertAfter($customSelect);
             
               for (var i = 0; i < selectOptions; i++) {
                   $('<li />', {
                       text: $this.children('option').eq(i).text(),
                       rel: $this.children('option').eq(i).val(),
                   }).appendTo($optionlist);
               }
             
               var $optionlistItems = $optionlist.children('li');
             
               $customSelect.click(function(e) {
                   e.stopPropagation();
                   $('div.tf-select-custom.active').not(this).each(function(){
                       $(this).removeClass('active').next('ul.select-options').hide();
                   });
                   $(this).toggleClass('active').next('ul.select-options').slideToggle();
               });
             
               $optionlistItems.click(function(e) {
                   e.stopPropagation();
                   $customSelect.text($(this).text()).removeClass('active');
                   $this.val($(this).attr('rel'));
                   $optionlist.hide();
               });
             
               $(document).click(function() {
                   $customSelect.removeClass('active');
                   $optionlist.hide();
               });

               $('.close-option').click(function() {
                $customSelect.removeClass('active');
                $optionlist.hide();
            });
           
           });
    }

    var removePreloader = function () {
        $("#preloader").fadeOut("slow", function () {
            setTimeout(function () {
                $("#preloader").remove();
            }, 1000);
        });
    };

    

    // Dom Ready
    $(function () {
        Modal_Right();
        menu_Modal_Left();
        headerFixed();
        themesflatSearch();
        pagetitleVideo();
        blogLoadMore();
        goTop();
        customizable_carousel_div();
        bg_bottom();
        tfvideo();
        Category_menu();
        productCarousel();
        custom_select()
        tftabs();
        tf_language();
    });
    $(window).on('load',function() {
        removePreloader();
    });
})(jQuery);
