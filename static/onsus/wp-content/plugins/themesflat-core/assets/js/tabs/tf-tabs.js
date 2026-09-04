;(function($) {

    "use strict";
    var blogPostsOwl = function($scope) {
        if ( $().owlCarousel ) {
            $scope.find('.tf-posts.has-carousel,.tf-products.has-carousel').each(function(){
                var
                $this = $(this),
                item = $this.data("column"),
                item2 = $this.data("column2"),
                item3 = $this.data("column3"),
                prev_icon = $this.data("prev_icon"),
                next_icon = $this.data("next_icon");

                var loop = false;
                if ($this.data("loop") == 'yes') {
                    loop = true;
                }

                var arrow = false;
                if ($this.data("arrow") == 'yes') {
                    arrow = true;
                } 

                var bullets = false;
                if ($this.data("bullets") == 'yes') {
                    bullets = true;
                }

                var auto = false;
                if ($this.data("auto") == 'yes') {
                    auto = true;
                }  

                $this.find('.owl-carousel').owlCarousel({
                    loop: loop,
                    margin: 0,
                    nav: arrow,
                    dots: bullets,
                    autoplay: auto,
                    autoplayTimeout: 5000,
                    smartSpeed: 850,
                    autoplayHoverPause: true,
                    navText : ["<i class=\""+prev_icon+"\"></i>","<i class=\""+next_icon+"\"></i>"],
                    responsive: {
                        0:{
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

    var productOptions = function () { 
        $('.product-option .thumb').on('click', function (e) {

            if ($(this).hasClass('active')) {
                e.preventDefault;
            } else {
                $(this).parent().find(".thumb.active").each(function () {
                    $(this).removeClass('active');
                });
                $(this).addClass('active');
                var options_img = $(this).data("src");

                $(this).closest('.item').find('.image img').removeClass('none animated fadeIn').fadeOut(200, function () {
                    $(this).attr('src', options_img);
                    $(this).addClass('animated fadeIn').fadeIn(100);
                });
            }
        });

    }

    var tf_countdown = function(){
        $('.tf-countdown').each(function(){
            var endDate = $(this).data('date');
            $(this).countdown( endDate, function(event) {
              var start_format = '<div class="countdown-inner">';
              // if(event.offset.days > 0) {  
                  var format_day =  '<div class="countdown-day"><div class="time"><strong>%D</strong></div><div class="text">Days</div></div>';
                  var format_hour = '<div class="countdown-hour"><div class="time"><strong>%H</strong></div><div class="text">Hours</div></div>';
                  var format_min = '<div class="countdown-min"><div class="time"><strong>%M</strong></div><div class="text">Mins</div></div>';
                  var format_sec = '<div class="countdown-sec"><div class="time"><strong>%S</strong></div><div class="text">Secs</div></div>';
                  
                  var end_format = '</div>'; 
                  $(this).html(event.strftime(start_format +  format_day + format_hour + format_min + format_sec + end_format));
              // }
          });
        });
        // $(".tf-products .item ").each(function(){
        //     var height2 = $(this).outerHeight(true);
        //     $(this).children('.ounner').css("height", height2);
        // });
    }

    var tf_tab_filter = function ($scope) {
        $scope.find('.tf-tabs').each(function () {           
            $(this).find('.tab-filter-2').click( function(event) {
                
  
                if (event.preventDefault) {
                    event.preventDefault();
                } else {
                    event.returnValue = false;
                }
        
                var tab_filter = $(this).data('filter');
                // var style = $(this).data('style');
                var image = $(this).data('image');
                var sale = $(this).data('sale');
                var group_btn = $(this).data('group-btn');
                var thum = $(this).data('thum');
                var meta = $(this).data('meta');
                var title = $(this).data('title');
                var price = $(this).data('price');
                var save_price = $(this).data('save-price');
                var coutdown = $(this).data('coutdown');
                var skillbar = $(this).data('skillbar');
                var information = $(this).data('information');
                var delivery = $(this).data('delivery');
                var add_to_cart = $(this).data('add-to-cart');
    
                var post_page = $(this).data('post');
                $(this).closest('.tf-tabs').find('.tf-products').addClass('loading');
        
                // $(this).closest('.tf-tabs').find('.tf-products').fadeOut();
        
                var data = {
                    action: 'tab_filter_product',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    tab_filter: tab_filter,
                    // style: style,
                    image: image,
                    sale: sale,
                    group_btn: group_btn,
                    thum: thum,
                    meta: meta,
                    title: title,
                    price: price,
                    save_price: save_price,
                    coutdown: coutdown,
                    skillbar: skillbar,
                    information: information,
                    delivery: delivery,
                    add_to_cart: add_to_cart,

    
                };
        
                $.ajax({
                    type: 'product',
                    dataType: 'json',
                    // dataType: "html",
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $(this).closest('.tf-tabs').find('#product-tab-content-filter-2').html( data );
                        $(this).closest('.tf-tabs').find('#product-tab-content-filter-2').removeClass('loading');
                        //  $(this).closest('.tf-tabs').find('#product-tab-content-filter-2').fadeIn();
                        console.log( textStatus );
                        console.log( XMLHttpRequest );
                        tf_countdown();
                        productOptions();
  
                    }.bind(this),
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                        console.log( MLHttpRequest );
                        console.log( textStatus );
                        console.log( errorThrown );
                        $(this).closest('.tf-tabs').find('#product-tab-content-filter-2').html( 'No posts found' );
                        $(this).closest('.tf-tabs').find('#product-tab-content-filter-2').removeClass('loading');                    
                        //  $(this).closest('.tf-tabs').find('#product-tab-content-filter-2').fadeIn();
                    }.bind(this),
                    
                })
        
            });
            
        });

        // $(".tf-products .item ").each(function(){
        //     var height2 = $(this).outerHeight(true);
        //     $(this).children('.ounner').css("height", height2);
        // });
       
        
    }

    $(window).on('elementor/frontend/init', function() {
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tftabs.default', tftabs );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tf-tabs.default', tftabs );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tftabs.default', blogPostsOwl );
        elementorFrontend.hooks.addAction( 'frontend/element_ready/tftabs.default', tf_tab_filter );
    });

})(jQuery);
