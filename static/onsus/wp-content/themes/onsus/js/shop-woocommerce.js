;(function($) {

    'use strict'

    // Quantity Button
    var tf_QuantityButton = function() {        
       
        $(document).on('click', '.plus', function () {
            var $input = $(this).parents('.quantity').find('input[type="number"]');
            var value = parseInt($input.val());
        
            if (value > 0) {
                value = value + 1;
            } 
        
            $input.val(value);

            $input.val(value).trigger('change'); 
            $('button[name="update_cart"]').prop('disabled', false);
        });
        $(document).on('click', '.minus', function () {
            var $input = $(this).parents('.quantity').find('input[type="number"]');
            var value = parseInt($input.val());
        
            if (value > 1) {
                value = value - 1;
            }
        
            $input.val(value);

            $input.val(value).trigger('change'); 
            $('button[name="update_cart"]').prop('disabled', false);
        });
    }

    var tf_AddToCart = function() {
        $(document).on('click', '.btn-add-to-cart .add_to_cart', function(e) {
            var $thisbutton = $(this);
            e.preventDefault();
            var product_id = $thisbutton.data('product_id');

            var data = {
                product_id: product_id
            };

            $(document.body).trigger('adding_to_cart', [$thisbutton, data]);

            $.ajax({
                type: 'post',
                url: wc_add_to_cart_params.wc_ajax_url.replace(
                    '%%endpoint%%',
                    'add_to_cart'
                ),
                data: data,
                beforeSend: function(response) {
                    $thisbutton.removeClass('added').addClass('loading');
                },
                complete: function(response) {
                    $thisbutton.addClass('added').removeClass('loading');
                },
                success: function(response) {
                    tf_ToggleMiniCartType('show');

                    if (response.error & response.product_url) {
                        window.location = response.product_url;
                        return;
                    } else {
                        $(document.body).trigger('added_to_cart', [
                            response.fragments,
                            response.cart_hash
                        ]);
                    }
                }
            });

            return false;
        });
    } 

    var tf_ToggleMiniCart = function() {
        $(document).on('click', 'a.nav-cart-trigger', function(e) {
            e.preventDefault();
            $(".themesflat-top").css("z-index", "100");
            $("header").css("z-index", "1000");
            tf_ToggleMiniCartType('show');
        });

        $(document).on('click', '.minicart-close, .minicar-overlay', function(e) {
            $(".themesflat-top").css("z-index", "100000");
            $("header").css("z-index", "99");
            tf_ToggleMiniCartType('hide');
        });


        $(document).on('click', '.filter-button', function(e) {
            e.preventDefault();
            tf_ToggleFilter('show');
        });

        $(document).on('click', '.filter-close,.popup-filter .overlay', function(e) {
            tf_ToggleFilter('hide');
        });

        var adminbar = $("#wpadminbar").height();
        $(".header-cart-wrapper .nav-shop-cart").css({
            top: adminbar ,
        });

    }

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

    function tf_ToggleFilter(toggle_type){
        var toggle_element = $('.popup-filter'),
            toggle_class   = 'active';

        if(toggle_type == 'show'){
            toggle_element.addClass(toggle_class);
        }
        else if(toggle_type == 'hide'){
            toggle_element.removeClass(toggle_class);
        }
        else{
            toggle_element.toggleClass('active');
        }
    } 

    var tf_QuickView = function () {
        var qv_modal = $(document).find('#yith-quick-view-modal'),
            qv_overlay = qv_modal.find('.yith-quick-view-overlay'),
            qv_content = qv_modal.find('#yith-quick-view-content'),
            qv_close = qv_modal.find('#yith-quick-view-close'),
            qv_wrapper = qv_modal.find('.yith-wcqv-wrapper'),
            qv_wrapper_w = qv_wrapper.width(),
            qv_wrapper_h = qv_wrapper.height();

        $(document).off('click', '.tf-call-quickview').on('click', '.tf-call-quickview', function (e) {
            e.preventDefault();

            var t = $(this),
                product_id = t.data('product_id'),
                is_blocked = false;

            t.addClass('loading');

            if (typeof yith_qv.loader !== 'undefined') {
                is_blocked = true;
                t.block({
                    message: null,
                    overlayCSS: {
                        background: '#fff url(' + yith_qv.loader + ') no-repeat center',
                        opacity: 0.5,
                        cursor: 'none'
                    }
                });

                if (!qv_modal.hasClass('loading')) {
                    qv_modal.addClass('loading');
                }

                // stop loader
                $(document).trigger('qv_loading');
            }
            ajax_call(t, product_id, is_blocked);
        });

        var ajax_call = function (t, product_id, is_blocked) {
            $.ajax({
                url: yith_qv.ajaxurl,
                data: {
                    action: 'yith_load_product_quick_view',
                    product_id: product_id,
                    lang: yith_qv.lang,
                    context: 'frontend',
                },
                dataType: 'json',
                type: 'POST',
                success: function (data) {
                    qv_content.html(data.html);
                    // Variation Form
                    var form_variation = qv_content.find('.variations_form');
                    form_variation.each(function () {
                        $(this).wc_variation_form();
                        // add Color and Label Integration
                        if (typeof $.fn.yith_wccl !== 'undefined') {
                            $(this).yith_wccl();
                        } else if (typeof $.yith_wccl != 'undefined' && data.prod_attr) {

                            $.yith_wccl(data.prod_attr);
                        }
                    });
                    form_variation.trigger('check_variations');
                    form_variation.trigger('reset_image');

                    if (!qv_modal.hasClass('open')) {
                        qv_modal.removeClass('loading');

                    }
                }

            }).done(function() {
                qv_modal.addClass("open");
                t.removeClass('loading');
                tf_QuantityButton();
            });
        };
    }

    var tf_WishListAdd = function () {
        $(document).on('click', '.yith-add-to-wishlist-button-block:not(.added)', function (ev) {
            console.log('add wishlist');
            var $this = $(this),
                product_id = $this.data('product-id'),
                el_wrap = $this.closest('.yith-add-to-wishlist-button-block'),
                data = {
                    action: yith_wcwl_l10n.actions.add_to_wishlist_action,
                    context: 'frontend',
                    add_to_wishlist: product_id
                };

            $this.addClass('loading');
            ev.preventDefault();

            $.ajax({
                type: 'POST',
                url: yith_wcwl_l10n.ajax_url,
                data: data,
                dataType: 'json',
                success: function (response) {
                    el_wrap.addClass('added');
                    $this.removeClass('loading');
                }

            });

            return false;
        });
    }


    $(document).ready(function() {

        

        // var mode = localStorage.getItem('mode');
        var mode = 'grid';
        
        if (mode) 
            $('.products-content ul.products').addClass(mode);

        if (mode === 'list') {
            $('.toggle-products-layout-button.active').removeClass('active');
            $('.toggle-products-list-layout').addClass('active'); 
        } else if (mode === 'grid') {
            $('.toggle-products-layout-button.active').removeClass('active');
            $('.toggle-products-grid-layout').addClass('active'); 
        }
            
            
        $(".toggle-products-list-layout").click(function() {
            $('.products-content ul.products').addClass('loading');
            $('.toggle-products-layout-button.active').removeClass('active');
            $(this).addClass('active');
            $(".products-content ul.products").addClass("list");
            // localStorage.setItem('mode', 'list');
            setTimeout(function () {
                $('.products-content ul.products').removeClass('loading');
            }, 1000);
            
        });

        $(".toggle-products-grid-layout").click(function() {
            $('.products-content ul.products').addClass('loading');
            $('.toggle-products-layout-button.active').removeClass('active');
            $(this).addClass('active');
            $(".products-content ul.products").removeClass("list");
            // localStorage.setItem('mode', 'grid');

            setTimeout(function () {
                $('.products-content ul.products').removeClass('loading');                
            }, 1000);
           
        });


    });


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
    }

    var Search_Product = function () {
        $(document).on("click", function (e) {
            var clickID = e.target.id;
            if (clickID != "form_search_inner") {
                $("#form_search_inner").find('.result-search-products').hide();
                $("#form_search_inner").find('input.search-field').val('');
            }
        });


        if (the_ajax_script.ajax_search != '1') {
            return;
        }

        var xhr = null,
            searchCache = {},
            $form = $(document.body).find('form.products-search');

        $form.on('keyup', '.search-field', function (e) {
            var valid = false;

            if (typeof e.which == 'undefined') {
                valid = true;
            } else if (typeof e.which == 'number' && e.which > 0) {
                valid = !e.ctrlKey && !e.metaKey && !e.altKey;
            }

            if (!valid) {
                return;
            }

            if (xhr) {
                xhr.abort();
            }

            var $currentForm = $(this).closest('.products-search'),
                $search = $currentForm.find('input.search-field');

            if ($search.val().length < 2) {
                $currentForm.removeClass('searching searched actived found-products found-no-product invalid-length');
            }

            search($currentForm);
        })
        .on('change', '.dropdown_product_cat', function (e) {
            var valid = false;

            if (typeof e.which == 'undefined') {
                valid = true;
            } else if (typeof e.which == 'number' && e.which > 0) {
                valid = !e.ctrlKey && !e.metaKey && !e.altKey;
            }

            if (!valid) {
                return;
            }

            if (xhr) {
                xhr.abort();
            }

            var $currentForm = $(this).closest('.products-search'),
                $search = $currentForm.find('input.search-field');

            if ($search.val().length < 2) {
                $currentForm.removeClass('searching searched actived found-products found-no-product invalid-length');
            }

            search($currentForm);
        })
        .on('focusout', '.search-field', function () {
            var $currentForm = $(this).closest('.products-search'),
                $search = $currentForm.find('input.search-field');
            if ($search.val().length < 2) {
                $currentForm.removeClass('searching searched actived found-products found-no-product invalid-length');
            }
        });


        $(document).on('click', function (e) {
            if (!$form.hasClass('actived')) {
                return;
            }
            var target = e.target;

            if ($(target).closest('.products-search').length < 1) {
                $form.removeClass('searching searched actived found-products found-no-product invalid-length');
            }
        });

        /**
         * Private function for search
         */
        function search($currentForm) {
            var $search = $currentForm.find('input.search-field'),
                $select = $currentForm.find('select option:selected'),
                keyword = $search.val(),
                cat = $select.val(),
                $results = $currentForm.find('.result-search-products');

            var $loading = $currentForm.find('.search-submit');
                
            if (cat === "") {
                cat = 0;
            } 
            else cat = $select.val();

            if (keyword.trim().length < 2) {
                $currentForm.removeClass('searching found-products found-no-product').addClass('invalid-length');
                $results.hide();
                return;
            }
            
            $results.addClass('loading');
            $loading.addClass('loading');
            // $results.show();
            $currentForm.removeClass('found-products found-no-product').addClass('searching');

            var keycat = keyword + cat;

            if (keycat in searchCache) {
                var result = searchCache[keycat];

                $currentForm.removeClass('searching');

                $currentForm.addClass('found-products');

                $results.html(result.products);

                $(document.body).trigger('flat_ajax_search_request_success', [$results]);

                $currentForm.removeClass('invalid-length');

                $currentForm.addClass('searched actived');

                $results.removeClass('loading');
                $loading.removeClass('loading');
                $results.show();
            } else {
                $results.find('li').remove();
                if (typeof wc_add_to_cart_params === 'undefined') {
                var xhr = $.ajax({
                    url: the_ajax_script.ajaxurl,
                    method: 'POST',
                    dataType: 'json',
                    data: {
                        action: 'flat_search_products',
                        nonce: the_ajax_script.nonce,
                        term: keyword, 
                        cat: cat,
                        search_type: 'product',
                    },
                    success: function(response) {
                        if (response.success) {
                            var $products = response.data;
                            if ($products.length > 0) {
                                searchFormResult($currentForm, $results, $products);
                                $results.removeClass('loading');
                                $loading.removeClass('loading');
                                $results.show();
                            } else {
                                $results.html('<li class="item-search">Không tìm thấy sản phẩm nào.</li>');
                            }
                        } else {
                            console.log('Lỗi khi tìm kiếm.');
                        }
                    }
                });

                } else {
                    var data = {
                            'term': keyword,
                            'nonce': the_ajax_script.nonce,
                            'cat': cat,
                            'search_type': the_ajax_script.search_content_type
                        },
                        ajaxurl = wc_add_to_cart_params.wc_ajax_url.toString().replace('%%endpoint%%', 'flat_search_products');

                    var xhr = $.ajax({
                        url: the_ajax_script.ajaxurl,
                        method: 'POST',
                        dataType: 'json',
                        data: {
                            action: 'flat_search_products',
                            nonce: the_ajax_script.nonce,
                            term: keyword, 
                            cat: cat,
                            search_type: 'product', 
                        },
                        success: function(response) {
                            if (response.success) {
                                var $products = response.data;
                                if ($products.length > 0) {
                                    searchFormResult($currentForm, $results, $products);
                                    $results.removeClass('loading');
                                    $loading.removeClass('loading');
                                    $results.show();
                                } else {
                                    $results.html('<li class="item-search">Không tìm thấy sản phẩm nào.</li>');
                                }
                            } else {
                                console.log('Lỗi khi tìm kiếm.');
                            }
                        }
                    });

                }

            }
            
        }

        function searchFormResult($currentForm, $results, $products, keycat) {

            $currentForm.removeClass('searching');


            $currentForm.addClass('found-products');

            $results.html($products);

            $currentForm.removeClass('invalid-length');

            $(document.body).trigger('flat_ajax_search_request_success', [$results]);

            // Cache
            searchCache[keycat] = {
                found: true,
                products: $products
            };

            $currentForm.addClass('searched actived');
            $currentForm.find('.search-submit').hide();
            $currentForm.find('.clear-input').show();

        }
        $(".clear-input").on("click", function() {
            $(this).hide();
            $(this).closest('form').find(".input-search").val("");
            $(this).closest('form').find('.search-submit').show();  
        });
       
    };
   
    var Filter = function () {
        $('.sidebar').each(function(){
            $('.noUi-handle').on('click', function() {
                $(this).width(50);
              });
              var rangeSlider = $('.slider-range');
             
              for(var i=0;i<rangeSlider.length ;i++) {
                // var min = rangeSlider[i].data('min');
                // var max = rangeSlider[i].data('max');
                var currency = rangeSlider[i].dataset.currency;
            
                var moneyFormat = wNumb({
                    decimals: 0,
                    thousand: '',
                    prefix: currency
                });

                var min = rangeSlider[i].dataset.min;
                var max = rangeSlider[i].dataset.max;
                
                noUiSlider.create(rangeSlider[i], {
                  start: [min, max],
                  step: 1,
                  range: {
                    'min': parseInt(min),
                    'max': parseInt(max)
                  },
                  format: moneyFormat,
                  connect: true
                });
              // Set visual min and max values and also update value hidden form inputs
              
                rangeSlider[i].noUiSlider.on('update', function(values, handle) {
                  $('.slider-range-value1').html(values[0]) ;
                  $('.slider-range-value2').html(values[1]) ;
                  
                  // document.getElementById('slider-range-value1').innerHTML = values[0];
                  // document.getElementById('slider-range-value2').innerHTML = values[1];
            
                  // document.getElementsByName('min-value').value = moneyFormat.from(values[0]);
                  // document.getElementsByName('max-value').value = moneyFormat.from(values[1]);
                });
              }
              
            
            var post_page,paged;
            var selecetd_taxonomy = [];
            const name = [];
            var price_min,price_max,min,max,star;
            var id = [];

            

            $('.btn-clear-all').hide();
            $('.btn-clear-price').hide();
            $('.tax-filter-rating.price').off('click').on( 'click',function(event) {
                $('.btn-clear-all').show();
                $('.btn-clear-price').show();
                tf_ToggleFilter('hide');
                $('.woocommerce-pagination').css({ display: "none"});
                $('.products-content').addClass('loading');
                if ($(this).hasClass( "active" )) {
                    $($(this)).removeClass('active');

                } else {
                    post_page = 12;  
                   
                }

                var price_1 = $('#slider-range-value1').text();
                var price_2 = $('#slider-range-value2').text();
      
                $('.btn-clear-price').text (price_1 + " - " + price_2);
                $('.woocommerce-pagination').css({ display: "none"});

                if (event.preventDefault) {
                    event.preventDefault();
                } else {
                    event.returnValue = false;
                }
                

                function remove_character(str, char_pos) {
                    var part1 = str.substring(0, char_pos);
                    var part2 = str.substring(char_pos + 1, str.length);
                    return (part1 + part2);
                }
                
               
                min = remove_character($('#slider-range-value1').text(),0);
                max = remove_character($('#slider-range-value2').text(),0);
                
                
                
                post_page = 12;

                var data = {
                    action: 'filter_posts',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    taxonomy: selecetd_taxonomy,
                    name:name,
                    id:id,
                    star:star,
                    min:min,
                    max:max,
                    paged:1 ,
                };
                $.ajax({
                    type: 'product',
                    dataType: 'text',
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $('.products-content').html(data);
                        $('.products-content').removeClass('loading');
                        productOptions();
                        $( document ).trigger( 'tf_wcwl_init' );
                    },
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                       
                        $('.products-content').html( '<h3>No Product found</h3>' );
                        $('.products-content').removeClass('loading');    
                    }
                })
                if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                    $('.btn-clear-all').hide();
                }else{
                    $('.btn-clear-all').show();
                }
                $('.btn-clear-price').off('click').on( 'click',function() {
                    
                    $('.products-content').addClass('loading');
                    $(this).hide();
                    var rangeSlider = $('.slider-range');
                    
                    for(var i=0;i<rangeSlider.length ;i++) {
                    min = rangeSlider[i].dataset.min;
                    max = rangeSlider[i].dataset.max;
                    var currency = rangeSlider[i].dataset.currency;
            
                    var moneyFormat = wNumb({
                        decimals: 0,
                        thousand: '',
                        prefix: currency
                    });
                    rangeSlider[i].noUiSlider.set([min, max], true, true);
                    
                    var data = {
                        action: 'filter_posts',
                        afp_nonce: the_ajax_script.nonce,
                        post_page: post_page,
                        taxonomy: selecetd_taxonomy,
                        name:name,
                        id:id,
                        star:star,
                        min:min,
                        max:max,
                        paged:1 ,
                    };
                    $.ajax({
                        type: 'product',
                        dataType: 'text',
                        method: 'post',
                        url: the_ajax_script.ajaxurl,
                        data: data,
                        success: function( data, textStatus, XMLHttpRequest ) {
                            $('.products-content').html(data);
                            $('.products-content').removeClass('loading');
                            productOptions();
                            $( document ).trigger( 'tf_wcwl_init' );
                        },
                        error: function( MLHttpRequest, textStatus, errorThrown ) {
                            console.log( MLHttpRequest );
                            console.log( textStatus );
                            console.log( errorThrown );
                            $('.products-content').html( '<h3>No Product found</h3>' );
                            $('.products-content').removeClass('loading');    
                        }
                    });
                    }
                   
                    if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                        $('.btn-clear-all').hide();
                    }else{
                        $('.btn-clear-all').show();
                    }
                    
                    
                });
                

            });

            $('.tax-filter-rating.rating').off('click').on( 'click',function(event) {
                $(".btn-clear-rating").remove();
                $('.btn-clear-all').show();
                tf_ToggleFilter('hide');
                $('.tax-filter-rating.rating').removeClass('active');
                $('.woocommerce-pagination').css({ display: "none"});
                $('.products-content').addClass('loading');
                
                if ($(this).hasClass( "active" )) {
                    $($(this)).removeClass('active');
                   
                } else {
                    $(this).addClass('active');       
                    star = $('.tax-filter-rating.rating.active').data('star');
                    $('.filter-active').append(function() {
                        return '<span class="btn-clear-rating" > ' + star + ' Star</span>';
                    });
                    
                }
                $('.woocommerce-pagination').css({ display: "none"});

                

                if (event.preventDefault) {
                    event.preventDefault();
                } else {
                    event.returnValue = false;
                }
                

                
                star = $('.tax-filter-rating.rating.active').data('star');
                
                var data = {
                    action: 'filter_posts',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    taxonomy: selecetd_taxonomy,
                    name:name,
                    id:id,
                    star:star,
                    min:min,
                    max:max,
                    paged:1 ,
                };
                $.ajax({
                    type: 'product',
                    dataType: 'text',
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $('.products-content').html(data);
                        $('.products-content').removeClass('loading');
                        productOptions();
                        $( document ).trigger( 'tf_wcwl_init' );
                    },
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                        console.log( MLHttpRequest );
                        console.log( textStatus );
                        console.log( errorThrown );
                        $('.products-content').html( '<h3>No Product found</h3>' );
                        $('.products-content').removeClass('loading');    
                    }
                })
                if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                    $('.btn-clear-all').hide();
                }else{
                    $('.btn-clear-all').show();
                }

                $('.btn-clear-rating').off('click').on( 'click',function() {
                    
                    $('.products-content').addClass('loading');
                    $('.tax-filter-rating.rating').removeClass('active');
                    $(this).remove();
                    star = '';
                    var data = {
                        action: 'filter_posts',
                        afp_nonce: the_ajax_script.nonce,
                        post_page: post_page,
                        taxonomy: selecetd_taxonomy,
                        name:name,
                        id:id,
                        star:star,
                        min:min,
                        max:max,
                        paged:1 ,
                    };
                    $.ajax({
                        type: 'product',
                        dataType: 'text',
                        method: 'post',
                        url: the_ajax_script.ajaxurl,
                        data: data,
                        success: function( data, textStatus, XMLHttpRequest ) {
                            $('.products-content').html(data);
                            $('.products-content').removeClass('loading');
                            productOptions();
                            $( document ).trigger( 'tf_wcwl_init' );
                        },
                        error: function( MLHttpRequest, textStatus, errorThrown ) {
                            console.log( MLHttpRequest );
                            console.log( textStatus );
                            console.log( errorThrown );
                            $('.products-content').html( '<h3>No Product found</h3>' );
                            $('.products-content').removeClass('loading');    
                        }
                    })
                    if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                        $('.btn-clear-all').hide();
                    }else{
                        $('.btn-clear-all').show();
                    }
    
                })

            });

            $('.tax-filter-rating.taxonomy').off('click').on( 'click',function(event) {
                $('.btn-clear-all').show();
                tf_ToggleFilter('hide');
                $('.woocommerce-pagination').css({ display: "none"});
                $('.products-content').addClass('loading');
                
                if ($(this).hasClass( "active" )) {
                    $($(this)).removeClass('active');

                    var name_tax2 =$(this).attr('title');
                    $(".btn-clear-taxonomy." + name_tax2 ).remove();
                    
                    const removeIndex = selecetd_taxonomy.findIndex((item) => item === $(this).attr('title'));
                    selecetd_taxonomy.splice(removeIndex, 1);

                } else {
                    selecetd_taxonomy.push($(this).attr('title'));
                    post_page = 12;

                    var name_tax =$(this).attr('title');
                    var name_tax_2 =$(this).data('nametx');

                    $('.filter-active').append(function() {
                        return '<span class="btn-clear-taxonomy '+ name_tax +'" data-taxo="'+ name_tax +'"> ' + name_tax_2 + '</span>';
                    }); 
                    $(this).addClass('active');  
                       
                }

                $('.woocommerce-pagination').css({ display: "none"});

                if (event.preventDefault) {
                    event.preventDefault();
                } else {
                    event.returnValue = false;
                }
                
                star = $('.tax-filter-rating.rating.active').data('star');
                

                var data = {
                    action: 'filter_posts',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    taxonomy: selecetd_taxonomy,
                    name:name,
                    id:id,
                    star:star,
                    min:min,
                    max:max,
                    paged:1 ,
                };
                $.ajax({
                    type: 'product',
                    dataType: 'text',
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $('.products-content').html(data);
                        $('.products-content').removeClass('loading');
                        productOptions();
                        $( document ).trigger( 'tf_wcwl_init' );
                    },
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                        console.log( MLHttpRequest );
                        console.log( textStatus );
                        console.log( errorThrown );
                        $('.products-content').html( '<h3>No Product found</h3>' );
                        $('.products-content').removeClass('loading');    
                    }
                })

                if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                    $('.btn-clear-all').hide();
                }else{
                    $('.btn-clear-all').show();
                }
                $('.btn-clear-taxonomy').off('click').on( 'click',function() {
                    
                    $('.products-content').addClass('loading');
                    var name_tax =$(this).data('taxo');
                    
                    $(".tax-filter-rating.taxonomy.active." + name_tax + "").removeClass('active');
                    const removeIndext_clear = selecetd_taxonomy.findIndex((item) => item === $(this).data('taxo'));
                    selecetd_taxonomy.splice(removeIndext_clear, 1);
                    $(this).remove();
                    var data = {
                        action: 'filter_posts',
                        afp_nonce: the_ajax_script.nonce,
                        post_page: post_page,
                        taxonomy: selecetd_taxonomy,
                        name:name,
                        id:id,
                        star:star,
                        min:min,
                        max:max,
                        paged:1 ,
                    };
                    $.ajax({
                        type: 'product',
                        dataType: 'text',
                        method: 'post',
                        url: the_ajax_script.ajaxurl,
                        data: data,
                        success: function( data, textStatus, XMLHttpRequest ) {
                            $('.products-content').html(data);
                            $('.products-content').removeClass('loading');
                            productOptions();
                            $( document ).trigger( 'tf_wcwl_init' );
                        },
                        error: function( MLHttpRequest, textStatus, errorThrown ) {
                            console.log( MLHttpRequest );
                            console.log( textStatus );
                            console.log( errorThrown );
                            $('.products-content').html( '<h3>No Product found</h3>' );
                            $('.products-content').removeClass('loading');    
                        }
                    });
                    if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                        $('.btn-clear-all').hide();
                    }else{
                        $('.btn-clear-all').show();
                    }
                    
                });

               

            });

            $('.tax-filter').off('click').on( 'click',function(event) {
                $('.btn-clear-all').show();
                tf_ToggleFilter('hide');
                $('.woocommerce-pagination').css({ display: "none"});
                $('.products-content').addClass('loading');
                
                if ($(this).hasClass( "active" )) {
                    const removeIndex = id.findIndex((item) => item === $(this).data("id"));
                    id.splice(removeIndex, 1);
                    name.splice(removeIndex, 1);
                    var name_att2 =$(this).data('nameatt');
                    $(".btn-clear-attribute." + name_att2 ).remove();
                    $(this).closest('.tax-filter').removeClass('active');
                   
                } else {
                    name.push($(this).data("name"));
                    id.push($(this).data("id"));

                    var name_att =$(this).data('nameatt');
                    var id_att =$(this).data('id');

                    $('.filter-active').append(function() {
                        return '<span class="btn-clear-attribute '+ name_att +'" data-nameatt="'+ name_att +'" data-idatt="'+ id_att +'"> ' + name_att + '</span>';
                    }); 
                    $(this).closest('.tax-filter').addClass('active');
                    
                }

                
                $('.woocommerce-pagination').css({ display: "none"});

                if (event.preventDefault) {
                    event.preventDefault();
                } else {
                    event.returnValue = false;
                }
                

                var data = {
                    action: 'filter_posts',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    taxonomy: selecetd_taxonomy,
                    name:name,
                    id:id,
                    star:star,
                    min:min,
                    max:max,
                    paged:1 ,
                };
                $.ajax({
                    type: 'product',
                    dataType: 'text',
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $('.products-content').html(data);
                        $('.products-content').removeClass('loading');
                        productOptions();
                        $( document ).trigger( 'tf_wcwl_init' );
                    },
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                        console.log( MLHttpRequest );
                        console.log( textStatus );
                        console.log( errorThrown );
                        $('.products-content').html( '<h3>No Product found</h3>' );
                        $('.products-content').removeClass('loading');    
                    }
                })
                if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                    $('.btn-clear-all').hide();
                }else{
                    $('.btn-clear-all').show();
                }

                $('.btn-clear-attribute').off('click').on( 'click',function() {
                    
                    $('.products-content').addClass('loading');
                    var name_att = $(this).data('nameatt');
                    $(".tax-filter.active." + name_att ).removeClass( "active" );
                    const removeIndex_att = id.findIndex((item) => item === $(this).data("idatt"));
                    id.splice(removeIndex_att, 1);
                    name.splice(removeIndex_att, 1);
                    $(this).remove();
                    var data = {
                        action: 'filter_posts',
                        afp_nonce: the_ajax_script.nonce,
                        post_page: post_page,
                        taxonomy: selecetd_taxonomy,
                        name:name,
                        id:id,
                        star:star,
                        min:min,
                        max:max,
                        paged:1 ,
                    };
                    $.ajax({
                        type: 'product',
                        dataType: 'text',
                        method: 'post',
                        url: the_ajax_script.ajaxurl,
                        data: data,
                        success: function( data, textStatus, XMLHttpRequest ) {
                            $('.products-content').html(data);
                            $('.products-content').removeClass('loading');
                            productOptions();
                            $( document ).trigger( 'tf_wcwl_init' );
                        },
                        error: function( MLHttpRequest, textStatus, errorThrown ) {
                            console.log( MLHttpRequest );
                            console.log( textStatus );
                            console.log( errorThrown );
                            $('.products-content').html( '<h3>No Product found</h3>' );
                            $('.products-content').removeClass('loading');    
                        }
                    })
                    if (!$('.btn-clear-attribute').length && !$('.btn-clear-taxonomy').length && !$('.btn-clear-rating').length && ($(".btn-clear-price").css('display') == 'none')) {
                        $('.btn-clear-all').hide();
                    }else{
                        $('.btn-clear-all').show();
                    }
    
                })
                

            });
           
            $('.btn-clear-all').off('click').on( 'click',function() {
                $('.products-content').addClass('loading');
                $(".tax-filter.active,.tax-filter-rating.active").removeClass( "active" );

                $('.btn-clear-taxonomy').each(function(){
                    const removeIndext_clear = selecetd_taxonomy.findIndex((item) => item === $(this).data('taxo'));
                    selecetd_taxonomy.splice(removeIndext_clear, 1);
                })

                $('.btn-clear-attribute').each(function(){
                    const removeIndex_att = id.findIndex((item) => item === $(this).data("idatt"));
                    id.splice(removeIndex_att, 1);
                    name.splice(removeIndex_att, 1);
                })
                
                star ='';
                $(this).hide();
                $('.btn-clear-price').hide();
                $('.btn-clear-attribute,.btn-clear-taxonomy,.btn-clear-rating').remove();
                var rangeSlider = $('.slider-range');
                
                for(var i=0;i<rangeSlider.length ;i++) {
                min = rangeSlider[i].dataset.min;
                max = rangeSlider[i].dataset.max;
                var currency = rangeSlider[i].dataset.currency;
            
                var moneyFormat = wNumb({
                    decimals: 0,
                    thousand: '',
                    prefix: currency
                });
                rangeSlider[i].noUiSlider.set([min, max], true, true);
                }
                var data = {
                    action: 'filter_posts',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    taxonomy: selecetd_taxonomy,
                    name:name,
                    id:id,
                    star:star,
                    min:min,
                    max:max,
                    paged:1 ,
                };
                $.ajax({
                    type: 'product',
                    dataType: 'text',
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $('.products-content').html(data);
                        $('.products-content').removeClass('loading');
                        productOptions();
                        $( document ).trigger( 'tf_wcwl_init' );
                    },
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                        console.log( MLHttpRequest );
                        console.log( textStatus );
                        console.log( errorThrown );
                        $('.products-content').html( '<h3>No Product found</h3>' );
                        $('.products-content').removeClass('loading');    
                    }
                })

            })

            $( '.products-content' ).on( 'click', '.pagination-filter a', function( e ){
                e.preventDefault();
            
                paged = /[\?&]paged=(\d+)/.test( this.href ) && RegExp.$1;
                if (!paged) {
                    paged = 1;
                } else paged = /[\?&]paged=(\d+)/.test( this.href ) && RegExp.$1;
                
                var data = {
                    action: 'filter_posts',
                    afp_nonce: the_ajax_script.nonce,
                    post_page: post_page,
                    taxonomy: selecetd_taxonomy,
                    name:name,
                    id:id,
                    star:star,
                    min:min,
                    max:max,
                    paged:paged ,                    
                    
                };
                $.ajax({
                    type: 'product',
                    dataType: 'text',
                    method: 'post',
                    url: the_ajax_script.ajaxurl,
                    data: data,
                    success: function( data, textStatus, XMLHttpRequest ) {
                        $('.products-content').html(data);
                        $('.products-content').removeClass('loading');
                        productOptions();
                        $( document ).trigger( 'tf_wcwl_init' );
                    },
                    error: function( MLHttpRequest, textStatus, errorThrown ) {
                        console.log( MLHttpRequest );
                        console.log( textStatus );
                        console.log( errorThrown );
                        $('.products-content').html( '<h3>No Product found</h3>' );
                        $('.products-content').removeClass('loading');    
                    }
                })
            });

            // if (!$('.btn-clear-price,.btn-clear-all,.btn-clear-taxonomy,.btn-clear-rating,.btn-clear-attribute').length){
            //     $('.btn-clear-price').hide();
            // }
            
           
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

                $(this).closest('.inner').find('.attachment-woocommerce_thumbnail,.wp-post-image').removeClass('none animated fadeIn').fadeOut(100, function () {
                    $(this).attr('src', options_img);
                    $(this).addClass('animated fadeIn').fadeIn(500);
                });
                $(this).closest('.item').find('.img_thumbnail').removeClass('none animated fadeIn').fadeOut(100, function () {
                    $(this).attr('src', options_img);
                    $(this).addClass('animated fadeIn').fadeIn(500);
                });
            }
        });

    }

    var stickyContent = function () {
        if ($(".sticky-sidebar").length) {
         $(".sticky-sidebar").theiaStickySidebar();
         }
    };

    var tf_Accordions = function () {
        if (matchMedia("only screen and (max-width: 767px)").matches) {
            $('.tf-accordion-ft').each(function() {
                $(this).find('.accordion-heading').on('click', function () {
                    if (!$(this).closest('.tf-accordion-ft').is('.active')) {
                        $(this).closest('.tf-accordion-ft').toggleClass('active');
                    } else {
                        $(this).closest('.tf-accordion-ft').toggleClass('active');
                    }
                });
            });
        }
    };

    var tf_360_image_product = function() {
        // if ( $('body').hasClass('single-product')) {
        if ($('#product-360-image').length) {
            $('.product-360-image').TreeSixtyImageRotate({
                totalFrames: $('.product-360-image').data("image"),
                endFrame: $('.product-360-image').data("image")
            }).initTreeSixty();
            
            $(".button-360-image,.button-close-360-image,.overlay-360-image").on( "click", function() {
                if($('.content-product-360-image').hasClass('active')){
                    $('.content-product-360-image').removeClass('active');	
                }else{
                    $('.content-product-360-image').addClass('active');
                }
            });
        }
	}

    var tf_popup_form = function () {
        if ($("#tf_form_popup").length > 0) {
          setTimeout(function () {
            $("#tf_form_popup").modal('show');
          }, 500);
        }
    };
    
    var tf_popup_search = function () {
        $('.btn-search').on('click', function () {
            $("#tf_search_popup").modal('show');
        });
    }

    var tftabs = function() {   
     
        $('.tf-tabs-menu').each(function(){
            $(this).find('.tf-tabcontent').children().first().show();
            $(this).find('.tf-tabnav ul').children('li').on('click',function(){
                var liActive = $(this).index();
                var contentActive=$(this).siblings().removeClass('active').parents('.tf-tabs-menu').find('.tf-tabcontent').children().eq(liActive);
                contentActive.addClass('active').fadeIn("slow");
                contentActive.siblings().removeClass('active');
                $(this).addClass('active')
            });
        });
    }

    var add_to_cart_fixed = function () {
        $(window).on("load scroll resize", function () {
            if (matchMedia("only screen and (max-width: 767px)").matches) {
                if ($(".tf-add-to-cart").length > 0) {
                    var fixed = $(".tf-add-to-cart");
                    
                    $(".tf-add-to-cart .stock.in-stock").remove();
                    var footer_shop = $(".site-footer").offset().top,
                        top = $('.woocommerce-product-details__short-description').offset().top;

                    $(window).scroll(function () {
                        if ($(this).scrollTop() > top && $(this).scrollTop() < (footer_shop)) {
                            fixed.addClass("show").fadeIn(1000);
                            $(".go-top").addClass("button-cart"); 
                        } else  {
                            fixed.removeClass("show");
                            $(".go-top").removeClass("button-cart"); 
                        }
                    });
                };
            };
        });
           
    };


    var tf_AddToCartSingle = function() {
        $(document).on('submit', '.cart', function(event){
            event.preventDefault();
        })
        $(document).on( 'click', '.single_add_to_cart_button:not(.disabled,.lumise-customize-button)', function (e) {
            e.preventDefault();
    
            var $this = $(this),
                $form           = $this.closest('form.cart'),
                all_data        = $form.serialize(),
                product_qty     = $form.find('input[name=quantity]').val() || 1,
                product_id      = $form.find('input[name=product_id]').val() || $this.val(),
                variation_id    = $form.find('input[name=variation_id]').val() || 0;
    
            var product_variation_data = {};
            $(this).closest('form.cart').find('.variations select').each(function() {
                product_variation_data[$(this).attr('id')] = $(this).val();
            });

            var data = {
                product_id: product_id,
                product_sku: '',
                quantity: product_qty,
                variation_id: variation_id,
                variations: product_variation_data,
                all_data: all_data,
            };
    
            var productdata = data.all_data + '&product_id='+ data.product_id + '&product_sku='+ data.product_sku + '&quantity='+ data.quantity + '&variation_id='+ data.variation_id + '&variations='+ JSON.stringify( data.variations ) +'&action=add_to_cart_single';
    
            $( document.body ).trigger('adding_to_cart', [$this, productdata]);
    
            $.ajax({
                type: 'post',
                url: $form.attr('action') + '/?wc-ajax=add_to_cart_single',
                data: productdata,
    
                beforeSend: function () {
                    $this.removeClass('added').addClass('loading');
                },
    
                complete: function () {
                    $this.addClass('added').removeClass('loading');
                },
    
                success: function (response) {                    
                    $('.cart-alert,.woocommerce-notices-wrapper').remove();
                    if ( response.error & response.product_url ) {
                        window.location = response.product_url;
                        return;
                    } else {
                      
                        $(document.body).trigger('added_to_cart', [
                            response.fragments,
                            response.cart_hash
                        ]);
                       
                    }

                    tf_ToggleMiniCartType('show');
                    
                },
    
            });

            // $.ajax({
            //     url: wc_add_to_cart_params.ajax_url,
            //     type: 'POST',
            //     data: {
            //         action: 'add_to_cart_ajax', // Custom action name
            //         product_id: product_id,
            //         quantity: product_qty,
            //     },
            //     success: function(response) {
            //         if (response.success) {
            //             // Update cart contents, you can call WooCommerce's function to update the cart here
            //             $(document.body).trigger('added_to_cart', [response.fragments, response.cart_hash]);
                        
            //             // Optionally, show a success message or update cart preview
            //             alert('Product added to cart!');
            //         } else {
            //             alert('Error: Could not add product to cart.');
            //         }
            //     },
            //     error: function() {
            //         alert('Error: Could not add product to cart.');
            //     }
            // });
    
            return false;
        });

        
    } 

    var tf_multi_swiper = function() {
        $(".product-test").each(function(index, element){
                   
            var $this = $(this);
            $this.addClass("instance-" + index);
            $this.find(".swiper-button-prev").addClass("btn-prev-" + index);
            $this.find(".swiper-button-next").addClass("btn-next-" + index);
            var row = $this.data("row"),
                item4 = $this.data("column4"),
                item1 = $this.data("column"),
                item2 = $this.data("column2"),
                item3 = $this.data("column3");
            var swiper = new Swiper(".instance-" + index, {
                loop:false,
                observer: true,
                observeParents: true,
                slidesPerColumnFill: 'row',
                slidesPerColumn: row,
                spaceBetween: 15,
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },
                navigation: {
                    nextEl: '.swiper-button-next',
                    prevEl: '.swiper-button-prev',
                },
                breakpoints: {
                    0: {
                        observer: true,
                        observeParents: true,
                        slidesPerView: item4,
                        slidesPerColumn: row,
                        spaceBetween: 15,
                    },
                    500: {
                        observer: true,
                        observeParents: true,
                        slidesPerView: item3,
                        slidesPerColumn: row,
                        spaceBetween: 15,
                    },
                    767: {
                        observer: true,
                        observeParents: true,
                        slidesPerView: item2,
                        slidesPerColumn: row,
                        spaceBetween: 15,
                    },
                    1200: {
                        observer: true,
                        observeParents: true,
                        slidesPerView: item1,
                        slidesPerColumn: row,
                        spaceBetween: 15,
                    },
                },
                // nextButton: ".btn-next-" + index,
                // prevButton: ".btn-prev-" + index
            });
        });
    }

    var toggle_category = function () {
        $('.widget_filter_categories .children .toggle-category').on('click',function(){
            $(this).parent().toggleClass('show');
        })
    }

    var productcategory = function() {
        if ( $().owlCarousel ) {
            $('.wrap-product-category').each(function(){
                var
                $this = $(this),
                item = $this.data("column"),
                item2 = $this.data("column2"),
                item3 = $this.data("column3"),
                item4 = $this.data("column4")

                $this.find('.owl-carousel').owlCarousel({
                    loop: false,
                    margin: 0,
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

    var toggle_header = function() {
        $('.btn-toogle-bottom').on('click',function(){
            $(this).closest('#header-fixed-wrap').find('.header-bottom').slideToggle();
        })
    }

        function updateProgress($wrap, sold, stock, percent) {
        if (!$wrap || !$wrap.length) return;

        // If variation does not manage stock, hide (or you can decide to show only sold)
        if (stock === null || stock === undefined || stock === "") {
        $wrap.hide();
        return;
        }

        sold = parseInt(sold || 0, 10);
        stock = parseInt(stock || 0, 10);
        percent = parseInt(percent || 0, 10);

        // Your original condition was: if available > sold (odd). Better: show if stock > 0
        if (stock <= 0) {
        $wrap.hide();
        return;
        }

        $wrap.show();
        $wrap.find(".tf-progressbar__sold").text(sold);
        $wrap.find(".tf-progressbar__stock").text(stock);
        $wrap.find(".tf-progressbar__bar").css("width", percent + "%");
    }

    $(document).on("found_variation", "form.variations_form", function (e, variation) {
        var $wrap = $(".tf-progressbar");
        if (!variation) return;

        updateProgress(
        $wrap,
        variation.tf_sold,
        variation.tf_stock,
        variation.tf_percent
        );
    });

    $(document).on("reset_data", "form.variations_form", function () {
        $(".tf-progressbar").hide();
    });
    
// Dom Ready
$(function() { 
    tf_QuantityButton();
    tf_AddToCart();
    tf_ToggleMiniCart();
    tf_QuickView();
    // tf_WishListAdd();
    tf_countdown();
    Search_Product();  
    stickyContent();
    productOptions();
    Filter();
    tf_Accordions();
    tf_360_image_product();
    tf_popup_search();
    tftabs();
    add_to_cart_fixed();
    tf_AddToCartSingle();
    tf_multi_swiper();
    toggle_category();
    productcategory();
    toggle_header();
});
    
    $(window).on('load',function() {
        tf_popup_form();
    });
})(jQuery);